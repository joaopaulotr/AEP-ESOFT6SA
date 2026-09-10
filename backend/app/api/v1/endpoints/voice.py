from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from app.api.deps import get_voice_service
from app.schemas.voice import FalaRequest, TranscricaoResponse
from app.services.voice_service import VoiceService

router = APIRouter()


@router.post("/voice/transcricao", response_model=TranscricaoResponse)
async def transcrever(
    file: UploadFile = File(...),
    voice: VoiceService = Depends(get_voice_service),
):
    audio = await file.read()
    return TranscricaoResponse(texto=voice.transcrever(audio, file.filename or "audio.webm"))


@router.post("/voice/fala")
async def gerar_fala(
    payload: FalaRequest,
    voice: VoiceService = Depends(get_voice_service),
):
    audio = voice.sintetizar_fala(payload.texto)
    return Response(content=audio, media_type="audio/mpeg")
