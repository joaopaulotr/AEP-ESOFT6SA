from app.core.config import settings
from app.providers.factory import build_llm_provider
from app.providers.base import LLMProvider
from app.repositories.session_repository import SessionRepository
from app.services.interview_service import InterviewService
from app.services.synthesis_service import SynthesisService
from app.services.voice_service import VoiceService


def get_session_repository() -> SessionRepository:
    return SessionRepository()


def get_llm_provider() -> LLMProvider:
    return build_llm_provider(settings)


def get_interview_service() -> InterviewService:
    return InterviewService(llm=get_llm_provider())


def get_synthesis_service() -> SynthesisService:
    return SynthesisService(get_session_repository(), get_llm_provider())


def get_voice_service() -> VoiceService:
    return VoiceService()
