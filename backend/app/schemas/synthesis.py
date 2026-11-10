from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class Citation(BaseModel):
    """Trecho literal do participante, com a sessão de origem."""

    texto: str
    session_id: str


class Theme(BaseModel):
    tema: str
    pontos: list[str] = Field(default_factory=list)
    citacoes: list[Citation] = Field(default_factory=list)


class Synthesis(BaseModel):
    """Relatório de síntese — coleção syntheses.

    escopo "sessao": síntese de uma entrevista (session_id obrigatório).
    escopo "roteiro": síntese cruzada de todas as sessões de um roteiro (EV-33).
    """

    synthesis_id: str = Field(default_factory=lambda: str(uuid4()))
    escopo: Literal["sessao", "roteiro"]
    script_id: str
    session_id: str | None = None
    resumo: str
    temas: list[Theme] = Field(default_factory=list)
    divergencias: list[str] = Field(default_factory=list)
    lacunas: list[str] = Field(default_factory=list)
    sessoes_usadas: int = 0
    modelo: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _scope_matches_reference(self) -> "Synthesis":
        if self.escopo == "sessao" and not self.session_id:
            raise ValueError("síntese de sessão exige session_id")
        if self.escopo == "roteiro" and self.session_id:
            raise ValueError("síntese de roteiro não pertence a uma sessão")
        return self
