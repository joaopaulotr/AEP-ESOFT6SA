from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_interview_service, get_session_repository
from app.repositories.session_repository import SessionRepository
from app.schemas.interview import TurnRequest, TurnResponse
from app.services.interview_service import InterviewService

router = APIRouter()


@router.post("/turn/{session_id}", response_model=TurnResponse)
async def handle_turn(
    session_id: str,
    payload: TurnRequest,
    interview: InterviewService = Depends(get_interview_service),
    sessions: SessionRepository = Depends(get_session_repository),
):
    session = await sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    if session.finished:
        raise HTTPException(status_code=409, detail="A entrevista já foi encerrada.")

    session, fala = interview.run_turn(session, payload.texto)
    await sessions.save(session)

    return TurnResponse(
        fala=fala,
        finalizada=session.finished,
        indice_atual=session.current_index,
    )
