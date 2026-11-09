from fastapi import APIRouter, Depends

from app.api.deps import get_session_service, get_synthesis_service
from app.schemas.interview import InterviewState, SessionResponse, SynthesisResponse
from app.services.session_service import SessionService
from app.services.synthesis_service import SynthesisService

router = APIRouter()


@router.post("/session", response_model=SessionResponse)
async def create_new_session(sessions: SessionService = Depends(get_session_service)):
    state, pergunta = await sessions.start()
    return SessionResponse(session_id=state.session_id, pergunta=pergunta)


@router.get("/session/{session_id}", response_model=InterviewState)
async def get_session(session_id: str, sessions: SessionService = Depends(get_session_service)):
    return await sessions.get(session_id)


@router.post("/session/{session_id}/finish", response_model=InterviewState)
async def finish_session(session_id: str, sessions: SessionService = Depends(get_session_service)):
    return await sessions.finish(session_id)


@router.post("/session/{session_id}/synthesis", response_model=SynthesisResponse)
async def synthesize_session(
    session_id: str,
    synthesis: SynthesisService = Depends(get_synthesis_service),
):
    return SynthesisResponse(sintese=await synthesis.synthesize(session_id))
