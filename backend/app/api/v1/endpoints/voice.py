import io

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from openai import OpenAI

from app.core.config import settings

router = APIRouter()

client = OpenAI(api_key=settings.openai_api_key or None)


class FalaRequest(BaseModel):
    texto: str


@router.post("/voice/transcricao")
async def transcrever(file: UploadFile = File(...)):
    audio = await file.read()
    buffer = io.BytesIO(audio)
    buffer.name = file.filename or "audio.webm"
    transcription = client.audio.transcriptions.create(
        model="whisper-1",
        file=buffer,
    )
    return {"texto": transcription.text}


@router.post("/voice/fala")
async def falar(payload: FalaRequest):
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=payload.texto,
    ) as response:
        audio = response.read()
    return Response(content=audio, media_type="audio/mpeg")