from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.api.deps import get_speech_provider
from app.providers.base import SpeechProvider
from app.schemas.voice import SpeechRequest, TranscriptionResponse

router = APIRouter()


@router.post("/voice/transcricao", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    speech: SpeechProvider = Depends(get_speech_provider),
):
    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="Áudio vazio.")
    texto = await speech.transcribe(audio, file.filename or "audio.webm")
    return TranscriptionResponse(texto=texto)


@router.post("/voice/fala")
async def generate_speech(
    payload: SpeechRequest,
    speech: SpeechProvider = Depends(get_speech_provider),
):
    audio = await speech.synthesize(payload.texto)
    return Response(content=audio, media_type="audio/mpeg")
