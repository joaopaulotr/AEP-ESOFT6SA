from fastapi import APIRouter, Depends

from app.api.deps import get_session_service
from app.schemas.interview import TurnRequest, TurnResponse
from app.services.session_service import SessionService

router = APIRouter()


@router.post("/turn/{session_id}", response_model=TurnResponse)
async def handle_turn(
    session_id: str,
    payload: TurnRequest,
    sessions: SessionService = Depends(get_session_service),
):
    session, fala = await sessions.take_turn(session_id, payload.texto)
    return TurnResponse(
        fala=fala,
        finalizada=session.finished,
        indice_atual=session.current_index,
        **await sessions.turn_meta(session),
    )
