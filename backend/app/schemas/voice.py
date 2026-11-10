from pydantic import BaseModel, Field

from app.providers.base import Tom


class SpeechRequest(BaseModel):
    texto: str = Field(min_length=1)
    tom: Tom | None = None


class TranscriptionResponse(BaseModel):
    texto: str
