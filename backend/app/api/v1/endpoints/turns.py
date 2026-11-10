import json
import re
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_session_service
from app.core.errors import ConflictError, NotFoundError
from app.providers.base import ProviderError
from app.schemas.interview import TurnRequest, TurnResponse
from app.services.session_service import SessionService

router = APIRouter()

_PROVIDER_ERROR_DETAIL = "Falha ao se comunicar com o provedor de IA."
_ABBREVIATIONS = ("sr", "sra", "dr", "dra", "prof", "etc")
# Fim de frase: . ? ! … (com fechamentos opcionais) seguido de espaço.
_BOUNDARY = re.compile(r"[.?!…]+[\"')\]]*(?=\s)")


def split_sentences(text: str) -> list[str]:
    """Divide a fala em frases (. ? ! …), sem quebrar abreviações comuns nem decimais."""
    sentences: list[str] = []
    start = 0
    for match in _BOUNDARY.finditer(text):
        before = text[start : match.start()].split()
        last_word = before[-1].lower() if before else ""
        if match.group().startswith(".") and last_word in _ABBREVIATIONS:
            continue
        sentences.append(text[start : match.end()].strip())
        start = match.end()
    sentences.append(text[start:].strip())
    return [s for s in sentences if s]


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/turn/{session_id}", response_model=TurnResponse)
async def handle_turn(
    session_id: str,
    payload: TurnRequest,
    sessions: SessionService = Depends(get_session_service),
):
    return await _turn_response(sessions, session_id, payload.texto)


async def _turn_response(sessions: SessionService, session_id: str, texto: str) -> TurnResponse:
    session, fala = await sessions.take_turn(session_id, texto)
    return TurnResponse(
        fala=fala,
        finalizada=session.finished,
        indice_atual=session.current_index,
        **await sessions.turn_meta(session),
    )


@router.post("/turn/{session_id}/stream")
async def handle_turn_stream(
    session_id: str,
    payload: TurnRequest,
    sessions: SessionService = Depends(get_session_service),
):
    """Turno em SSE: `pensando` na hora, as frases da fala decidida e `fim`.

    O LLM é chamado uma vez e o turno é gravado antes de qualquer frase sair;
    404/409 iniciais respondem HTTP normal, falhas depois viram evento `erro`.
    """
    session = await sessions.get(session_id)  # 404 antes de abrir o stream
    if session.finished:
        raise ConflictError("A entrevista já foi encerrada.")

    async def events() -> AsyncIterator[str]:
        yield _sse("pensando", {})
        try:
            response = await _turn_response(sessions, session_id, payload.texto)
        except ProviderError:
            yield _sse("erro", {"detail": _PROVIDER_ERROR_DETAIL})
            return
        except (ConflictError, NotFoundError) as exc:
            yield _sse("erro", {"detail": exc.message})
            return
        for indice, frase in enumerate(split_sentences(response.fala)):
            yield _sse("frase", {"texto": frase, "indice": indice})
        yield _sse("fim", response.model_dump(mode="json"))

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
