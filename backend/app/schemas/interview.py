from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Turn(BaseModel):
    role: Literal["interviewer", "participant"]
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TurnRequest(BaseModel):
    texto: str = Field(min_length=1)


class TurnResponse(BaseModel):
    fala: str
    finalizada: bool
    indice_atual: int


class SessionResponse(BaseModel):
    session_id: str
    pergunta: str


class InterviewState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    asked_indices: list[int] = Field(default_factory=list)
    current_index: int = 0
    conversation: list[Turn] = Field(default_factory=list)
    profile: dict[str, str] = Field(default_factory=dict)
    finished: bool = False
    synthesis: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
