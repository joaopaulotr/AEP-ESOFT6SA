from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field

from app.schemas.participant import Participant
from app.schemas.script import DEFAULT_SCRIPT_ID, InterviewScript

Action = Literal["deepen", "advance", "finish"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Turn(BaseModel):
    """Uma fala da conversa (subdocumento de interview_sessions.conversation).

    pergunta_ordem: a pergunta central do roteiro a que a fala pertence
    (None no encerramento). acao: decisão que gerou a fala do entrevistador
    (None na abertura e nas falas do participante). latencia_ms: tempo da
    decisão do entrevistador.
    """

    role: Literal["interviewer", "participant"]
    text: str
    timestamp: datetime = Field(default_factory=_now)
    pergunta_ordem: int | None = None
    acao: Action | None = None
    latencia_ms: int | None = Field(default=None, ge=0)


class SessionMetrics(BaseModel):
    """Consumo da sessão (preenchido pelo EV-62)."""

    tokens: int = Field(default=0, ge=0)
    segundos_audio: float = Field(default=0.0, ge=0)
    custo_usd: float = Field(default=0.0, ge=0)


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
    """Sessão de entrevista — coleção interview_sessions.

    Referencia o roteiro (script_id) e, opcionalmente, o participante (participant_id).
    """

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    script_id: str = DEFAULT_SCRIPT_ID
    participant_id: str | None = None
    asked_indices: list[int] = Field(default_factory=list)
    current_index: int = 0
    conversation: list[Turn] = Field(default_factory=list)
    profile: dict[str, str] = Field(default_factory=dict)
    metricas: SessionMetrics = Field(default_factory=SessionMetrics)
    finished: bool = False
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    @computed_field  # gravado no documento para filtros e agregações
    @property
    def status(self) -> Literal["em_andamento", "concluida"]:
        return "concluida" if self.finished else "em_andamento"


class SessionDetails(BaseModel):
    """Sessão com o roteiro e o participante resolvidos via $lookup."""

    session: InterviewState
    script: InterviewScript | None
    participant: Participant | None


class ActionCount(BaseModel):
    acao: Action
    total: int


class QuestionDeepening(BaseModel):
    pergunta_ordem: int
    media_aprofundamentos: float


class ScriptStats(BaseModel):
    """Indicadores agregados das sessões de um roteiro (base do dashboard, EV-32)."""

    script_id: str
    total_sessoes: int = 0
    concluidas: int = 0
    taxa_conclusao: float = 0.0
    media_respostas: float = 0.0
    acoes: list[ActionCount] = Field(default_factory=list)
    aprofundamentos_por_pergunta: list[QuestionDeepening] = Field(default_factory=list)
