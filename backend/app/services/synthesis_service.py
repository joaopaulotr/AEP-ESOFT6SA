from app.prompts.synthesis_prompts import SYNTESIS_PROMPT
from app.providers.base import LLMProvider
from app.repositories.session_repository import SessionRepository
from app.services.interview_service import format_full_conversation


class SynthesisService:
    def __init__(self, session_repository: SessionRepository, llm: LLMProvider) -> None:
        self._sessions = session_repository
        self._llm = llm

    async def synthesize(self, session_id: str) -> str:
        interview_state = await self._sessions.get(session_id)
        if interview_state is None:
            raise ValueError("Sessão não encontrada.")
        if not interview_state.finished:
            raise ValueError("Não é possível gerar a síntese antes de encerrar a entrevista.")
        
        prompt = SYNTESIS_PROMPT.format(
            conversation=format_full_conversation(interview_state.conversation),
            profile=interview_state.profile,
        )
        synthesis = await self._llm.complete_text(prompt)
        interview_state.synthesis = synthesis
        await self._sessions.save(interview_state)
        return synthesis
