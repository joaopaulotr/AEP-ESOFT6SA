from pydantic import BaseModel, Field


class FalaRequest(BaseModel):
    texto: str = Field(min_length=1)


class TranscricaoResponse(BaseModel):
    texto: str
