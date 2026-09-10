from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    get_interview_service,
    get_session_repository,
    get_synthesis_service,
)
from app.repositories.session_repository import SessionRepository
from app.schemas.interview import InterviewState, SessionResponse, Turn
from app.services.interview_service import InterviewService
from app.services.synthesis_service import SynthesisService

router = APIRouter()


@router.post("/session", response_model=SessionResponse)
async def create_new_session(
    interview: InterviewService = Depends(get_interview_service),
    sessions: SessionRepository = Depends(get_session_repository),
):
    state = InterviewState()
    pergunta = interview.opening_question()
    state.conversation.append(Turn(role="interviewer", text=pergunta))
    await sessions.create(state)
    return SessionResponse(session_id=state.session_id, pergunta=pergunta)


@router.get("/session/{session_id}", response_model=InterviewState)
async def get_session(
    session_id: str,
    sessions: SessionRepository = Depends(get_session_repository),
):
    session = await sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    return session


@router.post("/session/{session_id}/synthesis")
async def synthesize_session(
    session_id: str,
    synthesis: SynthesisService = Depends(get_synthesis_service),
):
    return {"sintese": await synthesis.synthesize(session_id)}
