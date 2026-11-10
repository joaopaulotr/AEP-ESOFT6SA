from typing import Literal

from pydantic import BaseModel, Field


class SpeechRequest(BaseModel):
    texto: str = Field(min_length=1)
    tom: Literal["acolhedor", "neutro", "formal"] | None = None


class TranscriptionResponse(BaseModel):
    texto: str
