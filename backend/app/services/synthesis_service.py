import json

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.errors import ConflictError, NotFoundError
from app.core.usage import record_usage_safely, track_usage
from app.prompts.synthesis_prompts import (
    SCRIPT_SYNTHESIS_PROMPT,
    SYNTHESIS_FALLBACK_PROMPT,
    SYNTHESIS_PROMPT,
)
from app.providers.base import InvalidJSONError, LLMProvider, ProviderError
from app.repositories.script_repository import ScriptRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.synthesis_repository import SynthesisRepository
from app.schemas.synthesis import Citation, Synthesis, Theme
from app.services.citation_check import (
    filter_known_citations,
    filter_literal_citations,
    sanitize,
)
from app.services.interview_service import format_full_conversation

NO_ANSWERS_MESSAGE = "A entrevista não tem respostas para resumir."
MIN_SESSIONS_MESSAGE = (
    "Gere a síntese de pelo menos 2 entrevistas concluídas antes do relatório do roteiro."
)
SCRIPT_REPORT_NOT_READY = "Relatório do roteiro ainda não gerado."
MIN_SESSIONS_FOR_SCRIPT = 2
MAX_SESSIONS_FOR_SCRIPT = 30
MAX_SCRIPT_PROMPT_CHARS = 12_000  # entradas das sínteses no prompt do roteiro
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


class _LLMScriptTheme(BaseModel):
    tema: str = ""
    pontos: list[str] = Field(default_factory=list)
    citacoes: list[Citation] = Field(default_factory=list)

    @field_validator("pontos", mode="after")
    @classmethod
    def _strip(cls, values: list[str]) -> list[str]:
        return _clean_strings(values)


class _LLMScriptSynthesis(BaseModel):
    """Contrato do JSON que o LLM devolve para o relatório cruzado do roteiro."""

    resumo: str = Field(min_length=1)
    temas: list[_LLMScriptTheme] = Field(default_factory=list)
    divergencias: list[str] = Field(default_factory=list)
    lacunas: list[str] = Field(default_factory=list)

    @field_validator("resumo", mode="after")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("resumo vazio")
        return value

    @field_validator("divergencias", "lacunas", mode="after")
    @classmethod
    def _strip_items(cls, values: list[str]) -> list[str]:
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
        script_repository: ScriptRepository,
    ) -> None:
        self._sessions = session_repository
        self._syntheses = synthesis_repository
        self._llm = llm
        self._scripts = script_repository

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
            "conversation": sanitize(format_full_conversation(interview_state.conversation)),
            "profile": interview_state.profile,
        }
        with track_usage() as meter:
            try:
                parsed = await self._complete_structured(
                    SYNTHESIS_PROMPT.format(**prompt_args), _LLMSessionSynthesis
                )
                if parsed is None:  # JSON inválido nas duas tentativas: só o resumo em texto
                    resumo = await self._llm.complete_text(SYNTHESIS_FALLBACK_PROMPT.format(**prompt_args))
                    themes, gaps = [], []
                else:
                    resumo, gaps = parsed.resumo, parsed.lacunas
                    participant_texts = [
                        sanitize(turn.text)
                        for turn in interview_state.conversation
                        if turn.role == "participant"
                    ]
                    themes = self._build_themes(parsed, interview_state.session_id, participant_texts)
            finally:
                await record_usage_safely(self._sessions, session_id, meter)
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

    async def get_script(self, script_id: str) -> Synthesis:
        """Relatório cruzado já salvo (404 se o roteiro não existe ou ainda não há relatório)."""
        await self._require_script(script_id)
        saved = await self._syntheses.get_for_script(script_id)
        if saved is None:
            raise NotFoundError(SCRIPT_REPORT_NOT_READY)
        return saved

    async def synthesize_script(self, script_id: str, *, refresh: bool = False) -> Synthesis:
        """Relatório cruzado (map-reduce sobre as sínteses de sessão já salvas).

        Salvo e sem `refresh` -> devolve sem LLM. Com menos de 2 sínteses -> 409, também sem LLM."""
        await self._require_script(script_id)
        if not refresh:
            saved = await self._syntheses.get_for_script(script_id)
            if saved is not None:
                return saved
        inputs = await self._syntheses.list_session_syntheses(
            script_id, limit=MAX_SESSIONS_FOR_SCRIPT
        )
        if len(inputs) < MIN_SESSIONS_FOR_SCRIPT:
            raise ConflictError(MIN_SESSIONS_MESSAGE)

        inputs = self._fit_to_prompt_cap(inputs)
        payload = [
            {
                "session_id": item.session_id,
                "resumo": sanitize(item.resumo),
                "temas": [
                    {
                        "tema": sanitize(theme.tema),
                        "pontos": [sanitize(p) for p in theme.pontos],
                        "citacoes": [
                            {"texto": sanitize(c.texto), "session_id": c.session_id}
                            for c in theme.citacoes
                        ],
                    }
                    for theme in item.temas
                ],
            }
            for item in inputs
        ]
        prompt = SCRIPT_SYNTHESIS_PROMPT.format(syntheses=json.dumps(payload, ensure_ascii=False))
        # Sem sessão para atribuir o custo: o medidor só isola a operação, nada é gravado.
        with track_usage():
            parsed = await self._complete_structured(prompt, _LLMScriptSynthesis)
        if parsed is None:
            raise ProviderError("O modelo não devolveu um relatório cruzado válido.")

        known = [c for item in inputs for theme in item.temas for c in theme.citacoes]
        themes = [
            Theme(
                tema=theme.tema.strip(),
                pontos=theme.pontos,
                citacoes=filter_known_citations(theme.citacoes, known),
            )
            for theme in parsed.temas
            if theme.tema.strip()
        ]
        saved = await self._syntheses.save_for_script(
            Synthesis(
                escopo="roteiro",
                script_id=script_id,
                resumo=parsed.resumo,
                temas=themes,
                divergencias=parsed.divergencias,
                lacunas=parsed.lacunas,
                sessoes_usadas=len(inputs),
                modelo=self._llm.model_name,
            )
        )
        # Sessão apagada enquanto o LLM gerava: tira as citações dela (RK-11).
        removed = False
        for item in inputs:
            if item.session_id and not await self._sessions.exists(item.session_id):
                pulled = await self._syntheses.pull_citations_of_session(item.session_id)
                removed = removed or pulled > 0
        return await self._syntheses.get_for_script(script_id) if removed else saved

    @staticmethod
    def _fit_to_prompt_cap(inputs: list[Synthesis]) -> list[Synthesis]:
        """`inputs` vem das mais recentes para as mais antigas: corta as antigas que passam do
        limite de caracteres do prompt (sempre mantém pelo menos 2)."""
        kept: list[Synthesis] = []
        total = 0
        for item in inputs:
            size = len(item.model_dump_json(include={"resumo", "temas"}))
            if len(kept) >= MIN_SESSIONS_FOR_SCRIPT and total + size > MAX_SCRIPT_PROMPT_CHARS:
                break
            kept.append(item)
            total += size
        return kept

    async def _require_script(self, script_id: str) -> None:
        await self._scripts.get_or_raise(script_id)

    async def _complete_structured(self, prompt: str, model: type[BaseModel]):
        """JSON validado pelo Pydantic; inválido (fora do contrato ou JSON truncado) → tenta de
        novo uma vez → None. Outro ProviderError (queda, timeout) não é capturado: segue como 502."""
        for _ in range(STRUCTURED_ATTEMPTS):
            try:
                payload = await self._llm.complete_json(prompt)
                return model.model_validate(payload)
            except (ValidationError, InvalidJSONError):
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
