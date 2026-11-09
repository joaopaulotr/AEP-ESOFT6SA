from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_session_service, get_synthesis_service
from app.schemas.api import SessionCreate
from app.schemas.interview import (
    InterviewState,
    SessionDetails,
    SessionResponse,
    SynthesisResponse,
)
from app.schemas.synthesis import Synthesis
from app.services.session_service import SessionService
from app.services.synthesis_service import SynthesisService

router = APIRouter()


@router.post("/session", response_model=SessionResponse)
async def create_new_session(
    payload: SessionCreate | None = None,
    sessions: SessionService = Depends(get_session_service),
):
    """Corpo opcional: sem ele, abre no roteiro padrão (compatível com o front antigo)."""
    payload = payload or SessionCreate()
    return await sessions.open(payload.script_id, payload.participant_id)


@router.get("/session/{session_id}", response_model=InterviewState)
async def get_session(session_id: str, sessions: SessionService = Depends(get_session_service)):
    return await sessions.get(session_id)


@router.get("/session/{session_id}/detalhes", response_model=SessionDetails)
async def get_session_details(
    session_id: str, sessions: SessionService = Depends(get_session_service)
):
    return await sessions.details(session_id)


@router.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, sessions: SessionService = Depends(get_session_service)):
    await sessions.delete(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/session/{session_id}/finish", response_model=InterviewState)
async def finish_session(session_id: str, sessions: SessionService = Depends(get_session_service)):
    return await sessions.finish(session_id)


@router.post("/session/{session_id}/synthesis", response_model=SynthesisResponse)
async def synthesize_session(
    session_id: str,
    refresh: bool = False,
    synthesis: SynthesisService = Depends(get_synthesis_service),
):
    """Devolve a síntese salva; `?refresh=true` gera de novo (e paga o LLM)."""
    return SynthesisResponse(sintese=await synthesis.synthesize(session_id, refresh=refresh))


@router.get("/session/{session_id}/synthesis", response_model=Synthesis)
async def get_session_synthesis(
    session_id: str, synthesis: SynthesisService = Depends(get_synthesis_service)
):
    return await synthesis.get(session_id)
