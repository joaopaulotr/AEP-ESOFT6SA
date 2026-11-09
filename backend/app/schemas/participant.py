from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Participant(BaseModel):
    """Participante de entrevistas — coleção participants.

    Todos os dados de identificação são opcionais: a PoC não exige que a pessoa
    se identifique (ODS 10 / RK-11).
    """

    participant_id: str = Field(default_factory=lambda: str(uuid4()))
    apelido: str | None = None
    faixa_etaria: str | None = None
    regiao: str | None = None
    canal: Literal["voz", "texto"] = "voz"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
