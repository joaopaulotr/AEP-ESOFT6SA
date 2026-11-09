import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.db.seed import CORE_QUESTIONS
from app.main import app
from app.providers.base import ProviderError
from app.services.interview_service import InterviewService
from app.services.session_service import SessionService
from app.services.synthesis_service import SynthesisService


@pytest.fixture
def client(fake_llm):
    """App inteiro (lifespan, deps, repositórios) sobre o banco em memória do conftest;
    só o LLM é trocado pelo dublê."""
    interview = InterviewService(llm=fake_llm)
    app.dependency_overrides[deps.get_session_service] = lambda: SessionService(
        sessions=deps.get_session_repository(),
        scripts=deps.get_script_repository(),
        participants=deps.get_participant_repository(),
        interview=interview,
    )
    app.dependency_overrides[deps.get_synthesis_service] = lambda: SynthesisService(
        deps.get_session_repository(), deps.get_synthesis_repository(), fake_llm
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
    assert set(body) == {"session_id", "pergunta"}
    assert body["pergunta"] == CORE_QUESTIONS[0]


def test_session_document_references_the_seed_script(client):
    session_id = _abrir_sessao(client)

    body = client.get(f"/session/{session_id}").json()

    assert body["script_id"] == "entrevista-generalista"
    assert body["participant_id"] is None
    assert body["status"] == "em_andamento"
    assert "synthesis" not in body


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
    assert response.json()["detail"] == "A entrevista já foi encerrada."


def test_finish_unknown_session_returns_404(client):
    response = client.post("/session/inexistente/finish")

    assert response.status_code == 404
    assert response.json()["detail"] == "Sessão não encontrada."


def test_finish_marks_the_session_as_concluded(client):
    session_id = _abrir_sessao(client)

    body = client.post(f"/session/{session_id}/finish").json()

    assert body["finished"] is True and body["status"] == "concluida"


def test_synthesis_of_unknown_session_returns_404(client):
    response = client.post("/session/inexistente/synthesis")

    assert response.status_code == 404
    assert response.json()["detail"] == "Sessão não encontrada."


def test_startup_creates_indexes_and_the_seed(client):
    db = deps.get_database()

    async def _inspect():
        scripts = await db["interview_scripts"].count_documents({"script_id": "entrevista-generalista"})
        names = {
            name: set((await db[name].index_information()).keys())
            for name in ("interview_scripts", "participants", "interview_sessions", "syntheses")
        }
        return scripts, names

    scripts, names = client.portal.call(_inspect)

    assert scripts == 1
    assert "slug_convite_unico" in names["interview_scripts"]
    assert "participant_id_unico" in names["participants"]
    assert {"session_id_unico", "script_id_data", "participant_id"} <= names["interview_sessions"]
    assert {"synthesis_id_unico", "session_id", "script_id_escopo"} <= names["syntheses"]


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


def test_synthesis_when_provider_fails_returns_502(client, fake_llm):
    session_id = _abrir_sessao(client)
    client.post(f"/session/{session_id}/finish")
    fake_llm.queue_error(ProviderError("timeout"))

    response = client.post(f"/session/{session_id}/synthesis")

    assert response.status_code == 502
    assert response.json() == {"detail": "Falha ao se comunicar com o provedor de IA."}
