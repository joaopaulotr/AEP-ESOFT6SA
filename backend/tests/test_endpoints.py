import pytest
from fastapi.testclient import TestClient

from app.api.deps import (
    get_interview_service,
    get_session_repository,
    get_synthesis_service,
)
from app.main import app
from app.repositories.session_repository import SessionRepository
from app.services.interview_service import InterviewService
from app.services.synthesis_service import SynthesisService
from tests.conftest import FakeDB, FakeLLM


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def client(fake_llm):
    repository = SessionRepository(database=FakeDB())

    app.dependency_overrides[get_session_repository] = lambda: repository
    app.dependency_overrides[get_interview_service] = lambda: InterviewService(llm_client=fake_llm)
    app.dependency_overrides[get_synthesis_service] = lambda: SynthesisService(
        session_repository=repository, llm_client=fake_llm
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _abrir_sessao(client) -> str:
    return client.post("/session").json()["session_id"]


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_session_returns_id_and_opening_question(client):
    response = client.post("/session")

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"]
    assert body["pergunta"]


def test_turn_advances_the_interview_and_persists(client, fake_llm):
    session_id = _abrir_sessao(client)
    fake_llm.queue(action="deepen", next_utterance="Pode detalhar?")

    response = client.post(f"/turn/{session_id}", json={"texto": "é confuso"})

    assert response.status_code == 200
    assert response.json() == {"fala": "Pode detalhar?", "finalizada": False, "indice_atual": 0}

    conversa = client.get(f"/session/{session_id}").json()["conversation"]
    assert conversa[-1]["text"] == "Pode detalhar?"
    assert conversa[-2]["text"] == "é confuso"


def test_turn_on_unknown_session_returns_404(client):
    response = client.post("/turn/inexistente", json={"texto": "oi"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Sessão não encontrada."


def test_turn_rejects_empty_text(client):
    session_id = _abrir_sessao(client)

    response = client.post(f"/turn/{session_id}", json={"texto": ""})

    assert response.status_code == 422


def test_turn_on_finished_interview_returns_409(client, fake_llm):
    session_id = _abrir_sessao(client)
    for _ in range(4):
        fake_llm.queue(action="advance", next_utterance="")
        client.post(f"/turn/{session_id}", json={"texto": "respondi"})

    response = client.post(f"/turn/{session_id}", json={"texto": "mais uma"})

    assert response.status_code == 409


def test_get_unknown_session_returns_404(client):
    assert client.get("/session/inexistente").status_code == 404


def test_synthesis_before_finish_returns_400(client):
    session_id = _abrir_sessao(client)

    response = client.post(f"/session/{session_id}/synthesis")

    assert response.status_code == 400
    assert "encerrar a entrevista" in response.json()["detail"]


def test_synthesis_after_finish_returns_the_report(client, fake_llm):
    session_id = _abrir_sessao(client)
    for _ in range(4):
        fake_llm.queue(action="advance", next_utterance="")
        client.post(f"/turn/{session_id}", json={"texto": "respondi"})
    fake_llm.queue_payload("relatório de síntese")

    response = client.post(f"/session/{session_id}/synthesis")

    assert response.status_code == 200
    assert response.json() == {"sintese": "relatório de síntese"}
