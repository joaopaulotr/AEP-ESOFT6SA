import re
import unicodedata
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


# Roteiro "Entrevista generalista": as 4 perguntas fixas da v0.1.0 viraram dado.
# Sessões gravadas antes do multi-coleção (sem script_id) apontam para ele.
DEFAULT_SCRIPT_ID = "entrevista-generalista"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def slugify(text: str) -> str:
    """'Transporte Público 2026' -> 'transporte-publico-2026'."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


class Question(BaseModel):
    """Pergunta central de um roteiro (subdocumento de interview_scripts.perguntas)."""

    ordem: int = Field(ge=1)
    texto: str = Field(min_length=1)
    objetivo: str = ""
    max_aprofundamentos: int = Field(default=2, ge=0, le=5)

    @field_validator("texto")
    @classmethod
    def _texto_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("o texto da pergunta não pode ser vazio")
        return value.strip()


class ScriptOrigin(BaseModel):
    tipo: Literal["manual", "upload"] = "manual"
    arquivo: str | None = None
    extraido_em: datetime | None = None


class Persona(BaseModel):
    nome: str = "Ana"
    tom: Literal["acolhedor", "neutro", "formal"] = "acolhedor"


class InterviewScript(BaseModel):
    """Roteiro (campanha) de entrevista — coleção interview_scripts."""

    script_id: str = Field(default_factory=lambda: str(uuid4()))
    titulo: str = Field(min_length=1)
    tema: str = ""
    descricao: str = ""
    origem: ScriptOrigin = Field(default_factory=ScriptOrigin)
    perguntas: list[Question] = Field(min_length=1)
    persona: Persona = Field(default_factory=Persona)
    slug_convite: str = ""
    ativo: bool = True
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    @field_validator("perguntas")
    @classmethod
    def _ordered_and_unique(cls, perguntas: list[Question]) -> list[Question]:
        ordens = [pergunta.ordem for pergunta in perguntas]
        if len(set(ordens)) != len(ordens):
            raise ValueError("as perguntas não podem repetir a mesma ordem")
        return sorted(perguntas, key=lambda pergunta: pergunta.ordem)

    @model_validator(mode="after")
    def _default_slug(self) -> "InterviewScript":
        if not self.slug_convite:
            base = slugify(self.titulo) or "roteiro"
            self.slug_convite = f"{base}-{self.script_id[:8]}"
        else:
            self.slug_convite = slugify(self.slug_convite)
        return self
