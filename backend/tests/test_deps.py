import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app
from app.providers.fake import FakeLLMProvider, FakeSpeechProvider
from app.repositories.session_repository import SessionRepository
from app.services.interview_service import CORE_QUESTIONS, DEFAULT_CLOSING
from tests.conftest import FakeDB


@pytest.fixture(autouse=True)
def fake_backend(monkeypatch):
    monkeypatch.setattr(deps.settings, "llm_provider", "fake")
    deps.reset_dependencies()
    yield
    deps.reset_dependencies()


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
    repo = SessionRepository(database=FakeDB())
    app.dependency_overrides[deps.get_session_repository] = lambda: repo
    try:
        with TestClient(app) as client:
            session_id = client.post("/session").json()["session_id"]
            replies = [
                client.post(f"/turn/{session_id}", json={"texto": "resposta"}).json()
                for _ in CORE_QUESTIONS
            ]
    finally:
        app.dependency_overrides.clear()
    assert [r["finalizada"] for r in replies] == [False, False, False, True]
    assert replies[-1]["fala"] == DEFAULT_CLOSING
