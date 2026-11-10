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
        syntheses=deps.get_synthesis_repository(),
    )
    app.dependency_overrides[deps.get_synthesis_service] = lambda: SynthesisService(
        deps.get_session_repository(), deps.get_synthesis_repository(), fake_llm,
        deps.get_script_repository(),
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _abrir_sessao(client) -> str:
    return client.post("/api/v1/session").json()["session_id"]


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_routes_live_under_api_v1_and_health_stays_at_the_root(client):
    assert client.post("/session").status_code == 404
    assert client.post("/api/v1/session").status_code == 200
    assert client.get("/api/v1/health").status_code == 404


def test_create_session_returns_id_and_opening_question(client):
    response = client.post("/api/v1/session")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"session_id", "pergunta", "script_id", "titulo", "perguntas_total"}
    assert body["pergunta"].startswith("Oi, aqui é ") and body["pergunta"].endswith(CORE_QUESTIONS[0])


def test_session_document_references_the_seed_script(client):
    session_id = _abrir_sessao(client)

    body = client.get(f"/api/v1/session/{session_id}").json()

    assert body["script_id"] == "entrevista-generalista"
    assert body["participant_id"] is None
    assert body["status"] == "em_andamento"
    assert "synthesis" not in body


def test_turn_advances_the_interview_and_persists(client, fake_llm):
    session_id = _abrir_sessao(client)
    fake_llm.queue(action="deepen", next_utterance="Pode detalhar?")

    response = client.post(f"/api/v1/turn/{session_id}", json={"texto": "é confuso"})

    assert response.status_code == 200
    assert response.json() == {
        "fala": "Pode detalhar?", "finalizada": False, "indice_atual": 0,
        "acao": "deepen", "pergunta_ordem": 1, "perguntas_total": 4,
        "aprofundamentos_restantes": 1, "acolhimento": False,
    }

    conversa = client.get(f"/api/v1/session/{session_id}").json()["conversation"]
    assert conversa[-1]["text"] == "Pode detalhar?"
    assert conversa[-2]["text"] == "é confuso"


def test_turn_on_unknown_session_returns_404(client):
    response = client.post("/api/v1/turn/inexistente", json={"texto": "oi"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Sessão não encontrada."


def test_turn_rejects_empty_text(client):
    session_id = _abrir_sessao(client)

    response = client.post(f"/api/v1/turn/{session_id}", json={"texto": ""})

    assert response.status_code == 422


def test_turn_on_finished_interview_returns_409(client, fake_llm):
    session_id = _abrir_sessao(client)
    for _ in range(4):
        fake_llm.queue(action="advance", next_utterance="")
        client.post(f"/api/v1/turn/{session_id}", json={"texto": "respondi"})

    response = client.post(f"/api/v1/turn/{session_id}", json={"texto": "mais uma"})

    assert response.status_code == 409
    assert response.json()["detail"] == "A entrevista já foi encerrada."


def test_finish_unknown_session_returns_404(client):
    response = client.post("/api/v1/session/inexistente/finish")

    assert response.status_code == 404
    assert response.json()["detail"] == "Sessão não encontrada."


def test_finish_marks_the_session_as_concluded(client):
    session_id = _abrir_sessao(client)

    body = client.post(f"/api/v1/session/{session_id}/finish").json()

    assert body["finished"] is True and body["status"] == "concluida"


def test_synthesis_of_unknown_session_returns_404(client):
    response = client.post("/api/v1/session/inexistente/synthesis")

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
    assert client.get("/api/v1/session/inexistente").status_code == 404


def test_synthesis_before_finish_returns_400(client):
    session_id = _abrir_sessao(client)

    response = client.post(f"/api/v1/session/{session_id}/synthesis")

    assert response.status_code == 400
    assert "encerrar a entrevista" in response.json()["detail"]


def test_synthesis_without_participant_answers_returns_400(client, fake_llm):
    session_id = _abrir_sessao(client)
    client.post(f"/api/v1/session/{session_id}/finish")

    response = client.post(f"/api/v1/session/{session_id}/synthesis")

    assert response.status_code == 400
    assert response.json() == {"detail": "A entrevista não tem respostas para resumir."}
    assert fake_llm.prompts == []


def test_synthesis_after_finish_returns_the_report(client, fake_llm):
    session_id = _abrir_sessao(client)
    for _ in range(4):
        fake_llm.queue(action="advance", next_utterance="")
        client.post(f"/api/v1/turn/{session_id}", json={"texto": "respondi"})
    fake_llm.queue_payload({"resumo": "relatório de síntese"})

    response = client.post(f"/api/v1/session/{session_id}/synthesis")

    assert response.status_code == 200
    assert response.json() == {"sintese": "relatório de síntese"}


def test_synthesis_when_provider_fails_returns_502(client, fake_llm):
    session_id = _abrir_sessao(client)
    fake_llm.queue(action="advance", next_utterance="")
    client.post(f"/api/v1/turn/{session_id}", json={"texto": "respondi"})
    client.post(f"/api/v1/session/{session_id}/finish")
    fake_llm.queue_error(ProviderError("timeout"))

    response = client.post(f"/api/v1/session/{session_id}/synthesis")

    assert response.status_code == 502
    assert response.json() == {"detail": "Falha ao se comunicar com o provedor de IA."}


def test_startup_migrates_v010_sessions_and_their_synthesis(fake_db, monkeypatch):
    from datetime import datetime, timezone

    monkeypatch.setattr(deps.settings, "llm_provider", "fake")

    now = datetime.now(timezone.utc)

    async def _seed_legacy():
        await fake_db["interview_sessions"].insert_one(
            {"session_id": "antiga", "asked_indices": [], "current_index": 4, "conversation": [],
             "profile": {}, "finished": True, "synthesis": "Relatório antigo.",
             "created_at": now, "updated_at": now}
        )

    import anyio

    anyio.run(_seed_legacy)
    with TestClient(app) as client:
        body = client.get("/api/v1/session/antiga").json()

        async def _synthesis():
            return await fake_db["syntheses"].find_one({"session_id": "antiga"}, {"_id": 0})

        stored = client.portal.call(_synthesis)

    assert body["script_id"] == "entrevista-generalista" and body["status"] == "concluida"
    assert stored["resumo"] == "Relatório antigo." and stored["modelo"] == "v0.1.0"


def test_corrupt_session_document_returns_500_without_its_content(client):
    db = deps.get_database()

    async def _corrupt():
        await db["interview_sessions"].insert_one(
            {"session_id": "ruim", "script_id": "x",
             "conversation": [{"role": "participant", "text": "Maria mora em SP", "acao": "pular"}]}
        )

    client.portal.call(_corrupt)
    response = client.get("/api/v1/session/ruim")

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno ao ler os dados."}
    assert "Maria" not in response.text


def test_turn_on_a_session_whose_script_was_deleted_closes_it(client, fake_llm):
    session_id = _abrir_sessao(client)
    db = deps.get_database()

    async def _delete_script():
        await db["interview_scripts"].delete_many({})

    client.portal.call(_delete_script)
    response = client.post(f"/api/v1/turn/{session_id}", json={"texto": "vou de ônibus"})

    assert response.status_code == 200
    assert response.json()["finalizada"] is True
    assert fake_llm.prompts == []


def test_turn_overtaken_by_finish_returns_409_in_portuguese(client, fake_llm):
    session_id = _abrir_sessao(client)
    original = fake_llm.complete_json

    async def slow_decision(prompt):
        service = app.dependency_overrides[deps.get_session_service]()
        await service.finish(session_id)
        return await original(prompt)

    fake_llm.complete_json = slow_decision
    fake_llm.queue(action="deepen", next_utterance="Me conta mais?")

    response = client.post(f"/api/v1/turn/{session_id}", json={"texto": "resposta"})

    assert response.status_code == 409
    assert response.json() == {"detail": "A sessão foi alterada por outra ação. Tente de novo."}
    assert client.get(f"/api/v1/session/{session_id}").json()["finished"] is True


def test_startup_survives_a_v010_session_outside_the_model(fake_db, monkeypatch):
    from datetime import datetime, timezone

    import anyio

    monkeypatch.setattr(deps.settings, "llm_provider", "fake")
    now = datetime.now(timezone.utc)

    async def _seed():
        await fake_db["interview_sessions"].insert_one(
            {"session_id": "quebrada", "current_index": 0, "conversation": [],
             "profile": {"idade": 42}, "finished": False, "created_at": now, "updated_at": now}
        )

    anyio.run(_seed)
    with TestClient(app) as client:  # não pode falhar no startup
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/session/quebrada").status_code == 500


def test_startup_warns_when_frontend_url_is_localhost(monkeypatch, caplog):
    from app.core.config import settings
    from app.main import warn_default_frontend_url

    monkeypatch.setattr(settings, "frontend_url", "http://localhost:5173")
    with caplog.at_level("WARNING"):
        warn_default_frontend_url()
    assert "FRONTEND_URL" in caplog.text

    caplog.clear()
    monkeypatch.setattr(settings, "frontend_url", "https://entrevista.exemplo.org")
    with caplog.at_level("WARNING"):
        warn_default_frontend_url()
    assert "FRONTEND_URL" not in caplog.text


def test_validation_errors_are_422_in_portuguese_without_the_input(client):
    response = client.post("/api/v1/participants", json={"canal": "telepatia", "apelido": 5})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail.startswith("Dados inválidos: confira ") and "canal" in detail
    assert "telepatia" not in detail


def test_validation_error_without_field_names_the_body(client):
    response = client.post(
        "/api/v1/participants", content="{", headers={"content-type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["detail"].startswith("Dados inválidos: confira ")


def test_invalid_fields_skips_locations_and_repeats():
    from app.main import invalid_fields

    errors = [{"loc": ("body", "perguntas", 0, "texto")}, {"loc": ("query", "limit")}, {"loc": ("query", "limit")}, {"loc": ("body",)}]
    assert invalid_fields(errors) == ["perguntas.0.texto", "limit", "corpo da requisição"]
