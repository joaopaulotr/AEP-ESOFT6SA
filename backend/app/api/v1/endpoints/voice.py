from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.api.deps import get_voice_service
from app.core.config import settings
from app.schemas.voice import SpeechRequest, TranscriptionResponse
from app.services.voice_service import VoiceService

router = APIRouter()


@router.post("/voice/transcricao", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    session_id: str | None = None,
    voice: VoiceService = Depends(get_voice_service),
):
    audio = await file.read(settings.max_audio_bytes + 1)
    if not audio:
        raise HTTPException(status_code=400, detail="Áudio vazio.")
    if len(audio) > settings.max_audio_bytes:
        raise HTTPException(status_code=413, detail="Áudio maior que o permitido.")
    texto = await voice.transcribe(audio, file.filename or "audio.webm", session_id)
    if not texto.strip():
        raise HTTPException(status_code=400, detail="Não foi possível entender o áudio.")
    return TranscriptionResponse(texto=texto)


@router.post("/voice/fala")
async def generate_speech(
    payload: SpeechRequest,
    session_id: str | None = None,
    voice: VoiceService = Depends(get_voice_service),
):
    audio = await voice.synthesize(payload.texto, payload.tom, session_id)
    return Response(content=audio, media_type="audio/mpeg")
