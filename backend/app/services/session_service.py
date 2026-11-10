from app.core.errors import ConflictError, NotFoundError
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.script_repository import ScriptRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.synthesis_repository import SynthesisRepository
from app.schemas.api import SessionSummary
from app.schemas.interview import InterviewState, SessionDetails, SessionResponse
from app.schemas.script import InterviewScript
from app.services.interview_service import InterviewService


class SessionService:
    """Ciclo de vida de uma sessão: abrir, responder, encerrar e consultar.

    Liga as três coleções envolvidas (roteiro, participante, sessão) ao
    InterviewService, que só decide a conversa.
    """

    def __init__(
        self,
        sessions: SessionRepository,
        scripts: ScriptRepository,
        participants: ParticipantRepository,
        interview: InterviewService,
        syntheses: SynthesisRepository,
    ) -> None:
        self._sessions = sessions
        self._scripts = scripts
        self._participants = participants
        self._interview = interview
        self._syntheses = syntheses

    async def open(
        self, script_id: str | None = None, participant_id: str | None = None
    ) -> SessionResponse:
        """Abre a sessão e devolve o que a tela precisa para começar."""
        state, pergunta, script = await self._open(script_id, participant_id)
        return SessionResponse(
            session_id=state.session_id,
            pergunta=pergunta,
            script_id=script.script_id,
            titulo=script.titulo,
            perguntas_total=len(script.perguntas),
        )

    async def _open(
        self, script_id: str | None, participant_id: str | None
    ) -> tuple[InterviewState, str, InterviewScript]:
        if script_id is None:
            script = await self._scripts.get_default()
        else:
            script = await self._scripts.get_or_raise(script_id)
        if not script.ativo:
            raise ConflictError("Este roteiro não está recebendo entrevistas.")
        if participant_id is not None and not await self._participants.exists(participant_id):
            raise NotFoundError(ParticipantRepository.not_found_message)

        state = InterviewState(script_id=script.script_id, participant_id=participant_id)
        pergunta = self._interview.start(state, script)
        await self._sessions.create(state)
        return state, pergunta, script

    async def list_for_script(
        self, script_id: str, *, status: str | None = None, limit: int = 50
    ) -> list[SessionSummary]:
        await self._scripts.get_or_raise(script_id)  # roteiro inexistente -> 404
        return await self._sessions.list_summaries(script_id, status=status, limit=limit)

    async def get(self, session_id: str) -> InterviewState:
        return await self._sessions.get_or_raise(session_id)

    async def details(self, session_id: str) -> SessionDetails:
        details = await self._sessions.get_details(session_id)
        if details is None:
            raise NotFoundError(SessionRepository.not_found_message)
        return details

    async def delete(self, session_id: str) -> None:
        """Apaga a sessão e, em cascata, a síntese dela: a síntese deriva da fala do
        participante e não pode sobrar sem a sessão (RK-11). Síntese primeiro: se algo
        falhar no meio, sobra uma sessão sem síntese, que é regenerável."""
        await self._sessions.get_or_raise(session_id)
        await self._syntheses.delete_for_session(session_id)
        await self._sessions.delete(session_id)

    async def take_turn(self, session_id: str, text: str) -> tuple[InterviewState, str]:
        session = await self._sessions.get_or_raise(session_id)
        if session.finished:
            raise ConflictError("A entrevista já foi encerrada.")
        script = await self._scripts.get(session.script_id)
        if script is None:
            # Roteiro apagado com a sessão em andamento: guarda a resposta e encerra.
            session, fala = self._interview.close_with_answer(session, text)
        else:
            session, fala = await self._interview.run_turn(session, script, text)
        await self._persist(session)
        return session, fala

    async def finish(self, session_id: str) -> InterviewState:
        """Idempotente. Se um turno gravar no meio, relê e tenta de novo: encerrar
        sempre vence (quem clicou em Concluir não pode ficar com a sessão aberta)."""
        for attempt in range(2):
            session = await self._sessions.get_or_raise(session_id)
            if session.finished:
                return session
            self._interview.finish(session)
            try:
                await self._persist(session)
                return session
            except ConflictError:
                if attempt == 1:
                    raise
        raise AssertionError("inalcançável")  # pragma: no cover

    async def _persist(self, session: InterviewState) -> None:
        """Grava a sessão; versão velha vira ConflictError no repositório."""
        if not await self._sessions.save(session):
            raise NotFoundError(SessionRepository.not_found_message)  # apagada no meio
