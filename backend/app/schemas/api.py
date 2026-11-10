"""Modelos de entrada e saída da API que não são documentos do banco."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.script import Persona, ScriptOrigin


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
    origem: ScriptOrigin | None = None  # o front publica o rascunho mantendo a origem

    @field_validator("titulo")
    @classmethod
    def _titulo(cls, value: str) -> str:
        return _not_blank(value, "o título")


class DraftQuestion(BaseModel):
    texto: str
    objetivo: str = ""


class ScriptDraft(BaseModel):
    """Rascunho de roteiro vindo de um upload; não é gravado até o pesquisador publicar."""

    titulo: str
    tema: str = ""
    descricao: str = ""
    perguntas: list[DraftQuestion]
    origem: ScriptOrigin
    avisos: list[str] = Field(default_factory=list)


class ScriptUpdate(BaseModel):
    """Todos os campos são opcionais: só o que vier é alterado."""

    titulo: str | None = Field(default=None, min_length=1)
    tema: str | None = None
    descricao: str | None = None
    perguntas: list[QuestionCreate] | None = Field(default=None, min_length=1)
    persona: Persona | None = None  # persona: null é ignorado (não limpa; sempre há persona)
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
    link_convite: str = ""
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


class InvitePublic(BaseModel):
    """O que a pessoa convidada vê antes de começar: nada de sessão nem de participante."""

    slug: str
    titulo: str
    tema: str
    descricao: str
    persona: Persona
    perguntas_total: int
    link: str


class InviteLink(BaseModel):
    slug: str
    link: str


class InviteStart(BaseModel):
    """Entrada sem login: tudo opcional, texto vazio vira ausente."""

    canal: Literal["voz", "texto"] = "voz"
    apelido: str | None = Field(default=None, max_length=40)
    faixa_etaria: str | None = Field(default=None, max_length=20)
    regiao: str | None = Field(default=None, max_length=60)

    @field_validator("apelido", "faixa_etaria", "regiao", mode="before")
    @classmethod
    def _strip(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value


class ActionTotal(BaseModel):
    acao: str
    total: int


class QuestionDeepeningAvg(BaseModel):
    pergunta_ordem: int
    texto: str
    media: float


class ThemeCount(BaseModel):
    tema: str
    sessoes: int


class DayCount(BaseModel):
    dia: str  # AAAA-MM-DD no fuso America/Sao_Paulo
    total: int


class ChannelCount(BaseModel):
    canal: str
    total: int


class ScriptDashboard(BaseModel):
    """Painel do roteiro (EV-32): números agregados no banco a partir das sessões."""

    script_id: str
    titulo: str
    total_sessoes: int = 0
    concluidas: int = 0
    em_andamento: int = 0
    taxa_conclusao: float = 0.0
    duracao_media_min: float = 0.0
    media_respostas: float = 0.0
    acoes: list[ActionTotal] = Field(default_factory=list)
    aprofundamentos_por_pergunta: list[QuestionDeepeningAvg] = Field(default_factory=list)
    custo_total_usd: float = 0.0
    custo_medio_usd: float = 0.0
    temas_mais_citados: list[ThemeCount] = Field(default_factory=list)
    sessoes_por_dia: list[DayCount] = Field(default_factory=list)
    canais: list[ChannelCount] = Field(default_factory=list)
