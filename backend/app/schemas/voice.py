from pydantic import BaseModel, Field


class SpeechRequest(BaseModel):
    texto: str = Field(min_length=1)


class TranscriptionResponse(BaseModel):
    texto: str
