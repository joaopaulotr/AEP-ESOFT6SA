from app.core.errors import NotFoundError
from app.prompts.synthesis_prompts import SYNTESIS_PROMPT
from app.providers.base import LLMProvider
from app.repositories.session_repository import SessionRepository
from app.repositories.synthesis_repository import SynthesisRepository
from app.schemas.synthesis import Synthesis
from app.services.interview_service import format_full_conversation


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

        prompt = SYNTESIS_PROMPT.format(
            conversation=format_full_conversation(interview_state.conversation),
            profile=interview_state.profile,
        )
        resumo = await self._llm.complete_text(prompt)
        await self._syntheses.save_for_session(
            Synthesis(
                escopo="sessao",
                session_id=interview_state.session_id,
                script_id=interview_state.script_id,
                resumo=resumo,
                modelo=self._llm.model_name,
            )
        )
        return resumo
