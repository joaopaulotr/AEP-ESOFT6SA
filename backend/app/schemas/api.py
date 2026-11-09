"""Modelos de entrada e saída da API que não são documentos do banco."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.script import Persona


def _not_blank(value: str, campo: str) -> str:
    if not value.strip():
        raise ValueError(f"{campo} não pode ser vazio")
    return value.strip()


class QuestionCreate(BaseModel):
    texto: str = Field(min_length=1)
    objetivo: str = ""
    max_aprofundamentos: int = Field(default=2, ge=0, le=5)

    @field_validator("texto")
    @classmethod
    def _texto(cls, value: str) -> str:
        return _not_blank(value, "o texto da pergunta")


class ScriptCreate(BaseModel):
    titulo: str = Field(min_length=1)
    tema: str = ""
    descricao: str = ""
    perguntas: list[QuestionCreate] = Field(min_length=1)
    persona: Persona | None = None

    @field_validator("titulo")
    @classmethod
    def _titulo(cls, value: str) -> str:
        return _not_blank(value, "o título")


class ScriptUpdate(BaseModel):
    """Todos os campos são opcionais: só o que vier é alterado."""

    titulo: str | None = Field(default=None, min_length=1)
    tema: str | None = None
    descricao: str | None = None
    perguntas: list[QuestionCreate] | None = Field(default=None, min_length=1)
    persona: Persona | None = None
    ativo: bool | None = None

    @field_validator("titulo")
    @classmethod
    def _titulo(cls, value: str | None) -> str | None:
        return None if value is None else _not_blank(value, "o título")


class ScriptSummary(BaseModel):
    script_id: str
    titulo: str
    tema: str
    descricao: str
    slug_convite: str
    ativo: bool
    perguntas_total: int
    persona: Persona
    sessoes_total: int = 0
    concluidas: int = 0
    em_andamento: int = 0


class SessionSummary(BaseModel):
    session_id: str
    script_id: str
    participant_id: str | None
    participante: str | None  # apelido
    status: Literal["em_andamento", "concluida"]
    respostas: int  # falas do participante
    created_at: datetime
    updated_at: datetime
    tem_sintese: bool


class ParticipantCreate(BaseModel):
    apelido: str | None = None
    faixa_etaria: str | None = None
    regiao: str | None = None
    canal: Literal["voz", "texto"] = "voz"


class ParticipantUpdate(BaseModel):
    """Só o que vier é alterado; null limpa o campo (exceto canal, que é obrigatório)."""

    apelido: str | None = None
    faixa_etaria: str | None = None
    regiao: str | None = None
    canal: Literal["voz", "texto"] | None = None


class SessionCreate(BaseModel):
    script_id: str | None = None
    participant_id: str | None = None
