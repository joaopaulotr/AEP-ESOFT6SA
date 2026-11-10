"""Rotas de sessões por roteiro, detalhes e exclusão em cascata (EV-03, EV-13)."""

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app
from app.schemas.interview import InterviewState, Turn
from app.schemas.synthesis import Synthesis

API = "/api/v1"
DEFAULT_ID = "entrevista-generalista"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(deps.settings, "llm_provider", "fake")  # nunca a OpenAI real
    with TestClient(app) as test_client:
        yield test_client


def _run(client, func, *args):
    return client.portal.call(func, *args)


def _roteiro(client, titulo="Transporte") -> dict:
    response = client.post(
        f"{API}/scripts",
        json={"titulo": titulo, "perguntas": [{"texto": "Como vem?"}, {"texto": "E a volta?"}]},
    )
    return response.json()


def _participante(client, apelido="Lia") -> dict:
    return client.post(f"{API}/participants", json={"apelido": apelido}).json()


def _gravar(client, **fields) -> InterviewState:
    state = InterviewState(**fields)
    _run(client, deps.get_session_repository().create, state)
    return state


class TestCreateSession:
    def test_without_body_uses_the_default_script_and_keeps_the_old_fields(self, client):
        response = client.post(f"{API}/session")

        assert response.status_code == 200
        body = response.json()
        assert {"session_id", "pergunta"} <= set(body)
        assert body["script_id"] == DEFAULT_ID
        assert body["titulo"]
        assert body["perguntas_total"] == 4

    def test_with_script_and_participant(self, client):
        script = _roteiro(client)
        person = _participante(client)

        body = client.post(
            f"{API}/session",
            json={"script_id": script["script_id"], "participant_id": person["participant_id"]},
        ).json()

        assert body["pergunta"].endswith(" Como vem?")
        assert (body["script_id"], body["titulo"], body["perguntas_total"]) == (
            script["script_id"], "Transporte", 2
        )
        stored = client.get(f"{API}/session/{body['session_id']}").json()
        assert stored["participant_id"] == person["participant_id"]

    def test_unknown_script_is_404_in_portuguese(self, client):
        response = client.post(f"{API}/session", json={"script_id": "nao-existe"})

        assert response.status_code == 404
        assert response.json() == {"detail": "Roteiro não encontrado."}

    def test_unknown_participant_is_404(self, client):
        response = client.post(f"{API}/session", json={"participant_id": "fantasma"})

        assert response.status_code == 404
        assert response.json() == {"detail": "Participante não encontrado."}

    def test_inactive_script_is_409(self, client):
        script = _roteiro(client)
        client.put(f"{API}/scripts/{script['script_id']}", json={"ativo": False})

        response = client.post(f"{API}/session", json={"script_id": script["script_id"]})

        assert response.status_code == 409
        assert response.json() == {"detail": "Este roteiro não está recebendo entrevistas."}

    def test_empty_json_body_is_the_same_as_no_body(self, client):
        assert client.post(f"{API}/session", json={}).json()["script_id"] == DEFAULT_ID


class TestListByScript:
    def test_summaries_resolve_nickname_answers_and_synthesis_newest_first(self, client):
        script = _roteiro(client)
        person = _participante(client, "Lia")
        older = _gravar(
            client,
            script_id=script["script_id"],
            participant_id=person["participant_id"],
            finished=True,
            conversation=[
                Turn(role="interviewer", text="Como vem?"),
                Turn(role="participant", text="De ônibus"),
                Turn(role="participant", text="E demora"),
            ],
        )
        newer = _gravar(client, script_id=script["script_id"])
        _run(
            client,
            deps.get_synthesis_repository().save_for_session,
            Synthesis(escopo="sessao", session_id=older.session_id, script_id=script["script_id"], resumo="r"),
        )
        # a sessão mais recente é a que mudou por último
        _run(client, deps.get_session_repository().save, newer)

        body = client.get(f"{API}/scripts/{script['script_id']}/sessions").json()

        assert [item["session_id"] for item in body] == [newer.session_id, older.session_id]
        assert set(body[0]) == {
            "session_id", "script_id", "participant_id", "participante", "status",
            "respostas", "created_at", "updated_at", "tem_sintese",
        }
        assert (body[0]["participante"], body[0]["status"], body[0]["respostas"], body[0]["tem_sintese"]) == (
            None, "em_andamento", 0, False
        )
        assert (body[1]["participante"], body[1]["status"], body[1]["respostas"], body[1]["tem_sintese"]) == (
            "Lia", "concluida", 2, True
        )

    def test_only_sessions_of_that_script(self, client):
        script = _roteiro(client)
        _gravar(client, script_id=script["script_id"])
        _gravar(client)  # roteiro padrão

        body = client.get(f"{API}/scripts/{script['script_id']}/sessions").json()

        assert len(body) == 1

    def test_status_filter_and_limit(self, client):
        script = _roteiro(client)
        for _ in range(3):
            _gravar(client, script_id=script["script_id"], finished=True)
        _gravar(client, script_id=script["script_id"])
        url = f"{API}/scripts/{script['script_id']}/sessions"

        assert len(client.get(url, params={"status": "concluida"}).json()) == 3
        assert len(client.get(url, params={"status": "em_andamento"}).json()) == 1
        assert len(client.get(url, params={"limit": 2}).json()) == 2

    def test_invalid_status_or_limit_is_422(self, client):
        script = _roteiro(client)
        url = f"{API}/scripts/{script['script_id']}/sessions"

        assert client.get(url, params={"status": "xyz"}).status_code == 422
        assert client.get(url, params={"limit": 0}).status_code == 422

    def test_unknown_script_is_404(self, client):
        response = client.get(f"{API}/scripts/nao-existe/sessions")

        assert response.status_code == 404
        assert response.json() == {"detail": "Roteiro não encontrado."}

    def test_empty_script_returns_an_empty_list(self, client):
        script = _roteiro(client)

        assert client.get(f"{API}/scripts/{script['script_id']}/sessions").json() == []


class TestDetails:
    def test_returns_session_script_and_participant(self, client):
        script = _roteiro(client)
        person = _participante(client)
        state = _gravar(
            client, script_id=script["script_id"], participant_id=person["participant_id"]
        )

        body = client.get(f"{API}/session/{state.session_id}/detalhes").json()

        assert body["session"]["session_id"] == state.session_id
        assert body["script"]["titulo"] == "Transporte"
        assert body["participant"]["apelido"] == "Lia"
        assert "_id" not in body["session"]

    def test_anonymous_session_has_null_participant(self, client):
        state = _gravar(client)

        body = client.get(f"{API}/session/{state.session_id}/detalhes").json()

        assert body["participant"] is None and body["script"]["script_id"] == DEFAULT_ID

    def test_unknown_is_404(self, client):
        response = client.get(f"{API}/session/nao-existe/detalhes")

        assert response.status_code == 404
        assert response.json() == {"detail": "Sessão não encontrada."}


class TestDeleteSession:
    def test_deletes_the_session_and_its_synthesis_in_cascade(self, client):
        state = _gravar(client, finished=True)
        other = _gravar(client, finished=True)
        syntheses = deps.get_synthesis_repository()
        for session in (state, other):
            _run(
                client,
                syntheses.save_for_session,
                Synthesis(escopo="sessao", session_id=session.session_id, script_id=DEFAULT_ID, resumo="r"),
            )

        response = client.delete(f"{API}/session/{state.session_id}")

        assert response.status_code == 204
        assert client.get(f"{API}/session/{state.session_id}").status_code == 404
        assert _run(client, syntheses.get_for_session, state.session_id) is None
        assert _run(client, syntheses.get_for_session, other.session_id) is not None  # só a dela

    def test_session_without_synthesis_is_deleted(self, client):
        state = _gravar(client)

        assert client.delete(f"{API}/session/{state.session_id}").status_code == 204

    def test_unknown_is_404(self, client):
        response = client.delete(f"{API}/session/nao-existe")

        assert response.status_code == 404
        assert response.json() == {"detail": "Sessão não encontrada."}

    def test_deleting_the_session_frees_the_participant_to_be_deleted(self, client):
        person = _participante(client)
        state = _gravar(client, participant_id=person["participant_id"])
        assert client.delete(f"{API}/participants/{person['participant_id']}").status_code == 409

        client.delete(f"{API}/session/{state.session_id}")

        assert client.delete(f"{API}/participants/{person['participant_id']}").status_code == 204


class TestSynthesisRoutes:
    def _sessao_concluida(self, client) -> str:
        return _gravar(
            client,
            finished=True,
            conversation=[Turn(role="interviewer", text="Oi?"), Turn(role="participant", text="Oi")],
        ).session_id

    def test_get_before_generating_is_404(self, client):
        session_id = self._sessao_concluida(client)

        response = client.get(f"{API}/session/{session_id}/synthesis")

        assert response.status_code == 404
        assert response.json() == {"detail": "Síntese ainda não gerada."}

    def test_get_unknown_session_is_404(self, client):
        response = client.get(f"{API}/session/nao-existe/synthesis")

        assert response.status_code == 404
        assert response.json() == {"detail": "Sessão não encontrada."}

    def test_post_then_get_returns_the_saved_synthesis(self, client):
        session_id = self._sessao_concluida(client)

        generated = client.post(f"{API}/session/{session_id}/synthesis").json()
        saved = client.get(f"{API}/session/{session_id}/synthesis").json()

        assert saved["resumo"] == generated["sintese"]
        assert saved["escopo"] == "sessao" and saved["session_id"] == session_id
        assert "_id" not in saved

    def test_second_post_does_not_call_the_llm_again_and_refresh_does(self, client, fake_llm):
        from app.services.synthesis_service import SynthesisService

        app.dependency_overrides[deps.get_synthesis_service] = lambda: SynthesisService(
            deps.get_session_repository(), deps.get_synthesis_repository(), fake_llm,
            deps.get_script_repository(),
        )
        try:
            session_id = self._sessao_concluida(client)
            fake_llm.queue_payload({"resumo": "v1"}).queue_payload({"resumo": "v2"})

            first = client.post(f"{API}/session/{session_id}/synthesis").json()
            second = client.post(f"{API}/session/{session_id}/synthesis").json()
            assert (first, second) == ({"sintese": "v1"}, {"sintese": "v1"})
            assert len(fake_llm.prompts) == 1

            refreshed = client.post(f"{API}/session/{session_id}/synthesis", params={"refresh": "true"})
            assert refreshed.json() == {"sintese": "v2"}
            assert client.get(f"{API}/session/{session_id}/synthesis").json()["resumo"] == "v2"
            assert len(fake_llm.prompts) == 2
        finally:
            app.dependency_overrides.clear()
