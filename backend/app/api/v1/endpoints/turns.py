import asyncio
import json
import logging
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
logger = logging.getLogger(__name__)

# Referência forte aos turnos em andamento: o loop só guarda referência fraca às tasks.
_pending_turns: set[asyncio.Task] = set()

_PROVIDER_ERROR_DETAIL = "Falha ao se comunicar com o provedor de IA."
_UNEXPECTED_DETAIL = "Não consegui processar sua resposta. Tente de novo."
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


def _turn_done(task: asyncio.Task) -> None:
    """Solta a task e recupera a exceção (evita "never retrieved" após desconexão),
    logando só o tipo: nada de repr, traceback ou texto do participante."""
    _pending_turns.discard(task)
    if not task.cancelled() and (exc := task.exception()) is not None:
        logger.error("Falha no turno após desconexão: %s", type(exc).__name__)


async def _turn_events(
    sessions: SessionService, session_id: str, texto: str
) -> AsyncIterator[str]:
    # O turno roda numa task protegida: se o cliente sair, a resposta é cancelada mas
    # a gravação (um LLM + save) termina, e a resposta dele não se perde.
    task = asyncio.ensure_future(_turn_response(sessions, session_id, texto))
    _pending_turns.add(task)
    task.add_done_callback(_turn_done)
    yield _sse("pensando", {})
    try:
        response = await asyncio.shield(task)
    except ProviderError:
        yield _sse("erro", {"detail": _PROVIDER_ERROR_DETAIL})
        return
    except (ConflictError, NotFoundError) as exc:
        yield _sse("erro", {"detail": exc.message})
        return
    except Exception as exc:  # nunca derrubar o stream sem avisar o front
        logger.error("Falha inesperada no turno em streaming: %s", type(exc).__name__)
        yield _sse("erro", {"detail": _UNEXPECTED_DETAIL})
        return
    for indice, frase in enumerate(split_sentences(response.fala)):
        yield _sse("frase", {"texto": frase, "indice": indice})
    yield _sse("fim", response.model_dump(mode="json"))


@router.post("/turn/{session_id}/stream")
async def handle_turn_stream(
    session_id: str,
    payload: TurnRequest,
    sessions: SessionService = Depends(get_session_service),
):
    """Turno em SSE: `pensando` na hora, as frases da fala decidida e `fim`.

    O LLM é chamado uma vez e o turno é gravado antes de qualquer frase sair, mesmo
    que o cliente desconecte no meio (a gravação não é cancelada). 404/409 iniciais
    respondem HTTP normal; falhas depois viram evento `erro`.
    """
    session = await sessions.get(session_id)  # 404 antes de abrir o stream
    if session.finished:
        raise ConflictError("A entrevista já foi encerrada.")
    return StreamingResponse(
        _turn_events(sessions, session_id, payload.texto),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
