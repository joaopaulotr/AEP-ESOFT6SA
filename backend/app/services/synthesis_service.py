from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.errors import NotFoundError
from app.core.usage import estimate_cost, track_usage
from app.prompts.synthesis_prompts import SYNTHESIS_FALLBACK_PROMPT, SYNTHESIS_PROMPT
from app.providers.base import LLMProvider
from app.repositories.session_repository import SessionRepository
from app.repositories.synthesis_repository import SynthesisRepository
from app.schemas.synthesis import Citation, Synthesis, Theme
from app.services.citation_check import filter_literal_citations
from app.services.interview_service import format_full_conversation

NO_ANSWERS_MESSAGE = "A entrevista não tem respostas para resumir."
STRUCTURED_ATTEMPTS = 2  # a 1ª tentativa + 1 retry quando o JSON vem inválido


def _clean_strings(values: list) -> list[str]:
    return [value.strip() for value in values if isinstance(value, str) and value.strip()]


class _LLMSessionTheme(BaseModel):
    tema: str = ""
    pontos: list[str] = Field(default_factory=list)
    citacoes: list[str] = Field(default_factory=list)

    @field_validator("pontos", "citacoes", mode="after")
    @classmethod
    def _strip(cls, values: list[str]) -> list[str]:
        return _clean_strings(values)


class _LLMSessionSynthesis(BaseModel):
    """Contrato do JSON que o LLM devolve para a síntese de uma sessão."""

    resumo: str = Field(min_length=1)
    temas: list[_LLMSessionTheme] = Field(default_factory=list)
    lacunas: list[str] = Field(default_factory=list)

    @field_validator("resumo", mode="after")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("resumo vazio")
        return value

    @field_validator("lacunas", mode="after")
    @classmethod
    def _strip_gaps(cls, values: list[str]) -> list[str]:
        return _clean_strings(values)


class SynthesisService:
    def __init__(
        self,
        session_repository: SessionRepository,
        synthesis_repository: SynthesisRepository,
        llm: LLMProvider,
    ) -> None:
        self._sessions = session_repository
        self._syntheses = synthesis_repository
        self._llm = llm

    async def get(self, session_id: str) -> Synthesis:
        """Síntese já salva da sessão (404 se a sessão não existe ou ainda não há síntese)."""
        await self._sessions.get_or_raise(session_id)
        saved = await self._syntheses.get_for_session(session_id)
        if saved is None:
            raise NotFoundError("Síntese ainda não gerada.")
        return saved

    async def synthesize(self, session_id: str, *, refresh: bool = False) -> str:
        """Devolve a síntese salva sem chamar o LLM (EV-13); `refresh` gera de novo."""
        interview_state = await self._sessions.get_or_raise(session_id)
        if not interview_state.finished:
            raise ValueError("Não é possível gerar a síntese antes de encerrar a entrevista.")
        if not refresh:
            saved = await self._syntheses.get_for_session(session_id)
            if saved is not None:
                return saved.resumo

        if not any(turn.role == "participant" for turn in interview_state.conversation):
            raise ValueError(NO_ANSWERS_MESSAGE)  # nada do participante para resumir

        prompt_args = {
            "conversation": format_full_conversation(interview_state.conversation),
            "profile": interview_state.profile,
        }
        with track_usage() as meter:
            try:
                parsed = await self._complete_structured(SYNTHESIS_PROMPT.format(**prompt_args))
                if parsed is None:  # JSON inválido nas duas tentativas: só o resumo em texto
                    resumo = await self._llm.complete_text(SYNTHESIS_FALLBACK_PROMPT.format(**prompt_args))
                    themes, gaps = [], []
                else:
                    resumo, gaps = parsed.resumo, parsed.lacunas
                    participant_texts = [
                        turn.text for turn in interview_state.conversation if turn.role == "participant"
                    ]
                    themes = self._build_themes(parsed, interview_state.session_id, participant_texts)
            finally:
                await self._sessions.add_metrics(session_id, meter, estimate_cost(meter))
        await self._syntheses.save_for_session(
            Synthesis(
                escopo="sessao",
                session_id=interview_state.session_id,
                script_id=interview_state.script_id,
                resumo=resumo,
                temas=themes,
                lacunas=gaps,
                modelo=self._llm.model_name,
            )
        )
        if not await self._sessions.exists(session_id):
            # Apagada enquanto o LLM gerava: a síntese derivaria de uma fala já removida (RK-11).
            await self._syntheses.delete_for_session(session_id)
            raise NotFoundError(SessionRepository.not_found_message)
        return resumo

    async def _complete_structured(self, prompt: str) -> _LLMSessionSynthesis | None:
        """JSON validado pelo Pydantic; inválido → tenta de novo uma vez → None.
        ProviderError não é capturado: segue como 502."""
        for _ in range(STRUCTURED_ATTEMPTS):
            payload = await self._llm.complete_json(prompt)
            try:
                return _LLMSessionSynthesis.model_validate(payload)
            except ValidationError:
                continue
        return None

    @staticmethod
    def _build_themes(
        parsed: _LLMSessionSynthesis, session_id: str, participant_texts: list[str]
    ) -> list[Theme]:
        return [
            Theme(
                tema=theme.tema.strip(),
                pontos=theme.pontos,
                citacoes=[
                    Citation(texto=quote, session_id=session_id)
                    for quote in filter_literal_citations(theme.citacoes, participant_texts)
                ],
            )
            for theme in parsed.temas
            if theme.tema.strip()
        ]
