"""Turno em streaming por frase (EV-60) e divisão em frases."""

import json

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.endpoints.turns import split_sentences
from app.main import app
from app.providers.base import ProviderError
from app.services.interview_service import InterviewService
from app.services.session_service import SessionService

API = "/api/v1"


@pytest.fixture
def client(fake_llm):
    interview = InterviewService(llm=fake_llm)
    app.dependency_overrides[deps.get_session_service] = lambda: SessionService(
        sessions=deps.get_session_repository(),
        scripts=deps.get_script_repository(),
        participants=deps.get_participant_repository(),
        interview=interview,
        syntheses=deps.get_synthesis_repository(),
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _events(response) -> list[tuple[str, dict]]:
    out = []
    for block in response.text.strip().split("\n\n"):
        name, data = block.split("\n")
        assert name.startswith("event: ") and data.startswith("data: ")
        out.append((name[7:], json.loads(data[6:])))
    return out


def _abrir(client) -> str:
    return client.post(f"{API}/session").json()["session_id"]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Entendi. Me conta mais?", ["Entendi.", "Me conta mais?"]),
        ("Oi! Tudo bem… E você?", ["Oi!", "Tudo bem…", "E você?"]),
        ("Falei com o Sr. Silva e a Dra. Ana.", ["Falei com o Sr. Silva e a Dra. Ana."]),
        ("A Sra. Lia, o Dr. Rui e o Prof. Edu, etc. vieram.", ["A Sra. Lia, o Dr. Rui e o Prof. Edu, etc. vieram."]),
        ("Gasto 1.5 horas. Muito?", ["Gasto 1.5 horas.", "Muito?"]),
        ("sem pontuação", ["sem pontuação"]),
        ("  Um.   Dois.  ", ["Um.", "Dois."]),
        ("", []),
    ],
)
def test_split_sentences(text, expected):
    assert split_sentences(text) == expected


def test_stream_emits_events_in_order_and_fim_matches_normal_turn(client, fake_llm):
    sid = _abrir(client)
    fake_llm.queue("deepen", "Entendi. Como é isso no dia a dia?")
    response = client.post(f"{API}/turn/{sid}/stream", json={"texto": "Trabalho à noite."})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    events = _events(response)
    assert [n for n, _ in events] == ["pensando", "frase", "frase", "fim"]
    assert events[0][1] == {}
    assert events[1][1] == {"texto": "Entendi.", "indice": 0}
    assert events[2][1] == {"texto": "Como é isso no dia a dia?", "indice": 1}
    fim = events[3][1]
    assert fim["fala"] == "Entendi. Como é isso no dia a dia?"
    assert fim["acao"] == "deepen" and fim["finalizada"] is False

    sid2 = _abrir(client)
    fake_llm.queue("deepen", "Entendi. Como é isso no dia a dia?")
    normal = client.post(f"{API}/turn/{sid2}", json={"texto": "Trabalho à noite."}).json()
    assert fim == normal


def test_provider_error_becomes_erro_event_and_retry_saves_one_turn(client, fake_llm, monkeypatch):
    sid = _abrir(client)
    real_take_turn = SessionService.take_turn

    async def down(self, session_id, text):
        raise ProviderError("fora")

    monkeypatch.setattr(SessionService, "take_turn", down)
    response = client.post(f"{API}/turn/{sid}/stream", json={"texto": "Oi"})

    events = _events(response)
    assert [n for n, _ in events] == ["pensando", "erro"]
    assert events[1][1] == {"detail": "Falha ao se comunicar com o provedor de IA."}

    monkeypatch.setattr(SessionService, "take_turn", real_take_turn)
    fake_llm.queue("deepen", "Me conta mais.")
    retry = client.post(f"{API}/turn/{sid}/stream", json={"texto": "Oi"})
    assert [n for n, _ in _events(retry)][-1] == "fim"
    session = client.portal.call(deps.get_session_repository().get_or_raise, sid)
    assert [t.role for t in session.conversation].count("participant") == 1


def test_unknown_session_is_404_before_streaming(client):
    r = client.post(f"{API}/turn/nao-existe/stream", json={"texto": "Oi"})
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/json")


def test_finished_session_is_409_before_streaming(client):
    sid = _abrir(client)
    client.post(f"{API}/session/{sid}/finish")
    r = client.post(f"{API}/turn/{sid}/stream", json={"texto": "Oi"})
    assert r.status_code == 409 and r.headers["content-type"].startswith("application/json")


def test_conflict_during_stream_becomes_erro_event(client, fake_llm, monkeypatch):
    from app.core.errors import ConflictError

    sid = _abrir(client)
    fake_llm.queue("deepen", "Me conta mais.")

    async def boom(self, session_id, text):
        raise ConflictError("A sessão mudou durante o turno.")

    monkeypatch.setattr(SessionService, "take_turn", boom)
    events = _events(client.post(f"{API}/turn/{sid}/stream", json={"texto": "Oi"}))
    assert [n for n, _ in events] == ["pensando", "erro"]
    assert events[1][1] == {"detail": "A sessão mudou durante o turno."}


def test_not_found_during_stream_becomes_erro_event(client, monkeypatch):
    from app.core.errors import NotFoundError

    sid = _abrir(client)

    async def gone(self, session_id, text):
        raise NotFoundError("Sessão não encontrada.")

    monkeypatch.setattr(SessionService, "take_turn", gone)
    events = _events(client.post(f"{API}/turn/{sid}/stream", json={"texto": "Oi"}))
    assert [n for n, _ in events] == ["pensando", "erro"]
    assert events[1][1] == {"detail": "Sessão não encontrada."}


def test_unexpected_error_becomes_generic_erro_and_logs_without_text(client, monkeypatch, caplog):
    sid = _abrir(client)

    async def broken(self, session_id, text):
        raise RuntimeError("segredo-do-participante")

    monkeypatch.setattr(SessionService, "take_turn", broken)
    with caplog.at_level("ERROR"):
        events = _events(client.post(f"{API}/turn/{sid}/stream", json={"texto": "segredo-do-participante"}))
    assert [n for n, _ in events] == ["pensando", "erro"]
    assert events[1][1] == {"detail": "Não consegui processar sua resposta. Tente de novo."}
    assert "RuntimeError" in caplog.text and "segredo-do-participante" not in caplog.text


def test_turn_is_saved_even_if_the_client_disconnects(client, fake_llm):
    import asyncio

    from app.api.v1.endpoints import turns

    sid = _abrir(client)
    fake_llm.queue("deepen", "Me conta mais.")

    async def run():
        sessions = app.dependency_overrides[deps.get_session_service]()
        gen = turns._turn_events(sessions, sid, "Trabalho à noite.")
        assert (await gen.__anext__()).startswith("event: pensando")
        await gen.aclose()  # cliente saiu logo após o `pensando`
        await asyncio.gather(*turns._pending_turns)

    client.portal.call(run)
    session = client.portal.call(deps.get_session_repository().get_or_raise, sid)
    roles = [t.role for t in session.conversation]
    assert roles.count("participant") == 1 and roles.count("interviewer") == 2  # abertura + resposta
