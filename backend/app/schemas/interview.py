from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Turn(BaseModel):
    role: Literal["interviewer", "participant"]
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InterviewState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    asked_indices: list[int] = Field(default_factory=list)
    current_index: int = 0
    conversation: list[Turn] = Field(default_factory=list)
    profile: dict[str, str] = Field(default_factory=dict)
    finished: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
