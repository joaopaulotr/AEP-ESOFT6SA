from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.api.deps import get_session_repository, get_speech_provider
from app.core.config import settings
from app.core.usage import estimate_cost, track_usage
from app.providers.base import SpeechProvider
from app.repositories.session_repository import SessionRepository
from app.schemas.voice import SpeechRequest, TranscriptionResponse

router = APIRouter()


async def _attribute(sessions: SessionRepository, session_id: str | None, meter) -> None:
    """Soma o uso de voz na sessão informada; sessão desconhecida é ignorada (não falha a voz)."""
    if session_id:
        await sessions.add_metrics(session_id, meter, estimate_cost(meter))


@router.post("/voice/transcricao", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    session_id: str | None = None,
    speech: SpeechProvider = Depends(get_speech_provider),
    sessions: SessionRepository = Depends(get_session_repository),
):
    audio = await file.read(settings.max_audio_bytes + 1)
    if not audio:
        raise HTTPException(status_code=400, detail="Áudio vazio.")
    if len(audio) > settings.max_audio_bytes:
        raise HTTPException(status_code=413, detail="Áudio maior que o permitido.")
    with track_usage() as meter:
        try:
            texto = await speech.transcribe(audio, file.filename or "audio.webm")
        finally:
            await _attribute(sessions, session_id, meter)
    if not texto.strip():
        raise HTTPException(status_code=400, detail="Não foi possível entender o áudio.")
    return TranscriptionResponse(texto=texto)


@router.post("/voice/fala")
async def generate_speech(
    payload: SpeechRequest,
    session_id: str | None = None,
    speech: SpeechProvider = Depends(get_speech_provider),
    sessions: SessionRepository = Depends(get_session_repository),
):
    with track_usage() as meter:
        try:
            audio = await speech.synthesize(payload.texto, payload.tom)
        finally:
            await _attribute(sessions, session_id, meter)
    return Response(content=audio, media_type="audio/mpeg")
