from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from app.api.deps import get_voice_service
from app.schemas.voice import SpeechRequest, TranscriptionResponse
from app.services.voice_service import VoiceService

router = APIRouter()


@router.post("/voice/transcricao", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    voice: VoiceService = Depends(get_voice_service),
):
    audio = await file.read()
    return TranscriptionResponse(texto=voice.transcribe(audio, file.filename or "audio.webm"))


@router.post("/voice/fala")
async def generate_speech(
    payload: SpeechRequest,
    voice: VoiceService = Depends(get_voice_service),
):
    audio = voice.synthesize_speech(payload.texto)
    return Response(content=audio, media_type="audio/mpeg")
