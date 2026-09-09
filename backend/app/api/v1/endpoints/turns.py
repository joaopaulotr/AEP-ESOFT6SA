from fastapi import APIRouter, Depends

from app.api.deps import get_interview_service, get_session_repository
from app.repositories.session_repository import SessionRepository
from app.services.interview_service import InterviewService

router = APIRouter()


@router.post("/turn/{session_id}")
async def handle_turn(
    session_id: str,
    interview: InterviewService = Depends(get_interview_service),
    sessions: SessionRepository = Depends(get_session_repository),
):
    ...
