from functools import lru_cache

from app.core.config import settings
from app.providers.base import LLMProvider, SpeechProvider
from app.providers.factory import build_llm_provider, build_speech_provider
from app.repositories.session_repository import SessionRepository
from app.services.interview_service import InterviewService
from app.services.synthesis_service import SynthesisService


@lru_cache(maxsize=1)
def get_session_repository() -> SessionRepository:
    return SessionRepository()


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    return build_llm_provider(settings)


@lru_cache(maxsize=1)
def get_speech_provider() -> SpeechProvider:
    return build_speech_provider(settings)


@lru_cache(maxsize=1)
def get_interview_service() -> InterviewService:
    return InterviewService(llm=get_llm_provider())


@lru_cache(maxsize=1)
def get_synthesis_service() -> SynthesisService:
    return SynthesisService(get_session_repository(), get_llm_provider())


def reset_dependencies() -> None:
    """Limpa os singletons (uso em testes)."""
    for getter in (
        get_session_repository,
        get_llm_provider,
        get_speech_provider,
        get_interview_service,
        get_synthesis_service,
    ):
        getter.cache_clear()
