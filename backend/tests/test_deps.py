import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app
from app.providers.fake import FakeLLMProvider, FakeSpeechProvider
from app.db.seed import CORE_QUESTIONS
from app.services.interview_service import DEFAULT_CLOSING


@pytest.fixture(autouse=True)
def fake_backend(monkeypatch):
    monkeypatch.setattr(deps.settings, "llm_provider", "fake")
    deps.reset_dependencies()
    yield
    deps.reset_dependencies()


def test_repositories_share_the_injected_database(fake_db):
    assert deps.get_database() is fake_db
    assert [repo._collection.name for repo in deps.get_repositories()] == [
        "interview_scripts",
        "participants",
        "interview_sessions",
        "syntheses",
    ]


def test_session_service_is_wired_to_the_singletons():
    service = deps.get_session_service()

    assert service is deps.get_session_service()
    assert service._sessions is deps.get_session_repository()
    assert service._scripts is deps.get_script_repository()
    assert service._participants is deps.get_participant_repository()
    assert service._interview is deps.get_interview_service()


def test_providers_follow_the_configured_backend():
    assert isinstance(deps.get_llm_provider(), FakeLLMProvider)
    assert isinstance(deps.get_speech_provider(), FakeSpeechProvider)


def test_interview_service_is_a_singleton():
    assert deps.get_interview_service() is deps.get_interview_service()


def test_services_share_the_same_llm_provider():
    assert (
        deps.get_interview_service()._llm
        is deps.get_synthesis_service()._llm
        is deps.get_llm_provider()
    )


def test_reset_dependencies_rebuilds_instances():
    first = deps.get_interview_service()
    deps.reset_dependencies()
    assert deps.get_interview_service() is not first


def test_graph_is_compiled_once():
    assert deps.get_interview_service()._graph is deps.get_interview_service()._graph


def test_full_interview_runs_offline_with_fake_providers():
    with TestClient(app) as client:
        session_id = client.post("/api/v1/session").json()["session_id"]
        replies = [
            client.post(f"/api/v1/turn/{session_id}", json={"texto": "resposta"}).json()
            for _ in CORE_QUESTIONS
        ]
        sintese = client.post(f"/api/v1/session/{session_id}/synthesis").json()
    assert [r["finalizada"] for r in replies] == [False, False, False, True]
    assert replies[-1]["fala"] == DEFAULT_CLOSING
    assert sintese == {"sintese": "Síntese gerada em modo offline (provider fake)."}
