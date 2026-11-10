"""Relatório cruzado do roteiro (EV-33): rotas, regras e cascata de citações."""

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app
from app.providers.base import ProviderError
from app.schemas.interview import InterviewState, Turn
from app.schemas.synthesis import Citation, Synthesis, Theme
from app.services.synthesis_service import SynthesisService

API = "/api/v1"
MIN_MSG = "Gere a síntese de pelo menos 2 entrevistas concluídas antes do relatório do roteiro."


@pytest.fixture
def client(monkeypatch, fake_llm):
    monkeypatch.setattr(deps.settings, "llm_provider", "fake")
    app.dependency_overrides[deps.get_synthesis_service] = lambda: SynthesisService(
        deps.get_session_repository(),
        deps.get_synthesis_repository(),
        fake_llm,
        deps.get_script_repository(),
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def run(client, func, *args):
    return client.portal.call(func, *args)


def make_script(client) -> str:
    response = client.post(f"{API}/scripts", json={"titulo": "T", "perguntas": [{"texto": "Como?"}]})
    return response.json()["script_id"]


def add_session_synthesis(client, script_id, falas, *, tema="Tempo", citacoes=None, resumo="r") -> str:
    state = InterviewState(
        script_id=script_id,
        finished=True,
        conversation=[Turn(role="interviewer", text="?")]
        + [Turn(role="participant", text=fala) for fala in falas],
    )
    run(client, deps.get_session_repository().create, state)
    cites = [
        Citation(texto=c, session_id=state.session_id)
        for c in (citacoes if citacoes is not None else falas[:1])
    ]
    run(
        client,
        deps.get_synthesis_repository().save_for_session,
        Synthesis(
            escopo="sessao",
            session_id=state.session_id,
            script_id=script_id,
            resumo=resumo,
            temas=[Theme(tema=tema, pontos=["p"], citacoes=cites)],
        ),
    )
    return state.session_id


def llm_report(sid_a, sid_b, **overrides) -> dict:
    data = {
        "resumo": "Cruzado.",
        "temas": [
            {
                "tema": "Tempo",
                "pontos": ["Todos demoram"],
                "citacoes": [
                    {"texto": "demoro duas horas", "session_id": sid_a},
                    {"texto": "perco muito tempo", "session_id": sid_b},
                ],
            }
        ],
        "divergencias": ["A prefere ônibus, B prefere metrô"],
        "lacunas": ["Custo"],
    }
    data.update(overrides)
    return data


@pytest.fixture
def two(client):
    script_id = make_script(client)
    a = add_session_synthesis(client, script_id, ["demoro duas horas"])
    b = add_session_synthesis(client, script_id, ["perco muito tempo"])
    return script_id, a, b


class TestMinimumSessions:
    def test_less_than_two_is_409_and_never_calls_the_llm(self, client, fake_llm):
        script_id = make_script(client)
        add_session_synthesis(client, script_id, ["uma fala"])

        response = client.post(f"{API}/scripts/{script_id}/sintese")

        assert response.status_code == 409
        assert response.json() == {"detail": MIN_MSG}
        assert fake_llm.prompts == []

    def test_unknown_script_is_404_on_post_and_get(self, client):
        assert client.post(f"{API}/scripts/nao-existe/sintese").status_code == 404
        assert client.get(f"{API}/scripts/nao-existe/sintese").status_code == 404


class TestGenerate:
    def test_get_before_generating_is_404(self, client):
        script_id = make_script(client)

        response = client.get(f"{API}/scripts/{script_id}/sintese")

        assert response.status_code == 404
        assert response.json() == {"detail": "Relatório do roteiro ainda não gerado."}

    def test_generates_saves_and_counts_sessions(self, client, fake_llm, two):
        script_id, a, b = two
        fake_llm.queue_payload(llm_report(a, b))

        response = client.post(f"{API}/scripts/{script_id}/sintese")

        body = response.json()
        assert response.status_code == 200
        assert body["escopo"] == "roteiro" and body["synthesis_id"] == f"roteiro:{script_id}"
        assert body["sessoes_usadas"] == 2 and body["session_id"] is None
        assert body["divergencias"] == ["A prefere ônibus, B prefere metrô"]
        assert body["lacunas"] == ["Custo"]
        assert [(c["texto"], c["session_id"]) for c in body["temas"][0]["citacoes"]] == [
            ("demoro duas horas", a),
            ("perco muito tempo", b),
        ]
        assert client.get(f"{API}/scripts/{script_id}/sintese").json()["resumo"] == "Cruzado."

    def test_prompt_carries_summaries_themes_and_cited_session_ids(self, client, fake_llm, two):
        script_id, a, b = two
        fake_llm.queue_payload(llm_report(a, b))

        client.post(f"{API}/scripts/{script_id}/sintese")

        prompt = fake_llm.last_prompt
        assert a in prompt and b in prompt
        assert "demoro duas horas" in prompt and "divergencias" in prompt

    def test_invented_or_misattributed_citation_is_dropped(self, client, fake_llm, two):
        script_id, a, b = two
        data = llm_report(a, b)
        data["temas"][0]["citacoes"] += [
            {"texto": "frase inventada", "session_id": a},
            {"texto": "perco muito tempo", "session_id": a},  # existe, mas na outra sessão
            {"texto": "DEMORO  duas horas", "session_id": a},  # normalização ok
        ]
        fake_llm.queue_payload(data)

        body = client.post(f"{API}/scripts/{script_id}/sintese").json()

        assert [(c["texto"], c["session_id"]) for c in body["temas"][0]["citacoes"]] == [
            ("demoro duas horas", a),
            ("perco muito tempo", b),
            ("DEMORO  duas horas", a),
        ]

    def test_existing_without_refresh_skips_llm_and_refresh_regenerates(self, client, fake_llm, two):
        script_id, a, b = two
        fake_llm.queue_payload(llm_report(a, b)).queue_payload(llm_report(a, b, resumo="Novo."))

        client.post(f"{API}/scripts/{script_id}/sintese")
        again = client.post(f"{API}/scripts/{script_id}/sintese").json()
        assert again["resumo"] == "Cruzado." and len(fake_llm.prompts) == 1

        refreshed = client.post(f"{API}/scripts/{script_id}/sintese", params={"refresh": "true"}).json()
        assert refreshed["resumo"] == "Novo." and len(fake_llm.prompts) == 2

    def test_uses_at_most_30_most_recent_session_syntheses(self, client, fake_llm):
        script_id = make_script(client)
        ids = [add_session_synthesis(client, script_id, [f"fala {i}"]) for i in range(32)]
        fake_llm.queue_payload(llm_report(ids[0], ids[1], temas=[]))

        body = client.post(f"{API}/scripts/{script_id}/sintese").json()

        assert body["sessoes_usadas"] == 30
        assert ids[-1] in fake_llm.last_prompt
        assert ids[0] not in fake_llm.last_prompt

    def test_invalid_json_retries_then_502(self, client, fake_llm, two):
        script_id, *_ = two
        fake_llm.queue_payload("lixo").queue_payload({"resumo": 1})

        response = client.post(f"{API}/scripts/{script_id}/sintese")

        assert response.status_code == 502 and len(fake_llm.prompts) == 2

    def test_provider_error_is_502(self, client, fake_llm, two):
        script_id, *_ = two
        fake_llm.queue_error(ProviderError("fora"))

        assert client.post(f"{API}/scripts/{script_id}/sintese").status_code == 502

    def test_other_scripts_sessions_are_not_used(self, client, fake_llm, two):
        script_id, a, b = two
        other = make_script(client)
        add_session_synthesis(client, other, ["de outro roteiro"])
        fake_llm.queue_payload(llm_report(a, b))

        body = client.post(f"{API}/scripts/{script_id}/sintese").json()

        assert body["sessoes_usadas"] == 2 and "de outro roteiro" not in fake_llm.last_prompt


class TestCascade:
    def test_deleting_a_session_removes_its_citations_from_script_reports(self, client, fake_llm, two):
        script_id, a, b = two
        fake_llm.queue_payload(llm_report(a, b))
        client.post(f"{API}/scripts/{script_id}/sintese")

        assert client.delete(f"{API}/session/{a}").status_code == 204

        cites = client.get(f"{API}/scripts/{script_id}/sintese").json()["temas"][0]["citacoes"]
        assert [(c["texto"], c["session_id"]) for c in cites] == [("perco muito tempo", b)]

    def test_pull_only_touches_citations_of_that_session(self, client, fake_llm, two):
        script_id, a, b = two
        other = make_script(client)
        run(
            client,
            deps.get_synthesis_repository().create,
            Synthesis(
                escopo="roteiro",
                script_id=other,
                resumo="x",
                temas=[Theme(tema="t", citacoes=[Citation(texto="k", session_id="outra")])],
            ),
        )

        client.delete(f"{API}/session/{a}")

        kept = run(client, deps.get_synthesis_repository().list_for_script, other)[0]
        assert len(kept.temas[0].citacoes) == 1

    def test_session_deleted_while_llm_runs_leaves_no_orphan_citation(self, client, fake_llm, two):
        script_id, a, b = two
        sessions = deps.get_session_repository()
        original = fake_llm.complete_json

        async def delete_then_answer(prompt):
            await sessions.delete(a)
            return await original(prompt)

        fake_llm.complete_json = delete_then_answer
        fake_llm.queue_payload(llm_report(a, b))

        body = client.post(f"{API}/scripts/{script_id}/sintese").json()

        assert [c["session_id"] for c in body["temas"][0]["citacoes"]] == [b]
