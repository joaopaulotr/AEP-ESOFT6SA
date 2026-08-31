from fastapi import APIRouter

from app.schemas.interview import InterviewState, Turn
from app.services.interview_service import get_opening_question
from app.services.session_service import create_session

router = APIRouter()


@router.post("/session")
async def create_new_session():
    ...
