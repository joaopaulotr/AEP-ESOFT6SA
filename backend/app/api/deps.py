from app.repositories.session_repository import SessionRepository
from app.services.interview_service import InterviewService
from app.services.synthesis_service import SynthesisService


def get_session_repository() -> SessionRepository:
    return SessionRepository()


def get_interview_service() -> InterviewService:
    return InterviewService()


def get_synthesis_service() -> SynthesisService:
    return SynthesisService()
