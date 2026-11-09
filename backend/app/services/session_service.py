from app.core.errors import ConflictError, NotFoundError
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.script_repository import ScriptRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.interview import InterviewState, SessionDetails
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
    ) -> None:
        self._sessions = sessions
        self._scripts = scripts
        self._participants = participants
        self._interview = interview

    async def start(
        self, script_id: str | None = None, participant_id: str | None = None
    ) -> tuple[InterviewState, str]:
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
        return state, pergunta

    async def get(self, session_id: str) -> InterviewState:
        return await self._sessions.get_or_raise(session_id)

    async def details(self, session_id: str) -> SessionDetails:
        details = await self._sessions.get_details(session_id)
        if details is None:
            raise NotFoundError(SessionRepository.not_found_message)
        return details

    async def take_turn(self, session_id: str, text: str) -> tuple[InterviewState, str]:
        session = await self._sessions.get_or_raise(session_id)
        if session.finished:
            raise ConflictError("A entrevista já foi encerrada.")
        script = await self._scripts.get(session.script_id)
        if script is None:
            raise NotFoundError("O roteiro desta entrevista não existe mais.")

        session, fala = await self._interview.run_turn(session, script, text)
        await self._sessions.save(session)
        return session, fala

    async def finish(self, session_id: str) -> InterviewState:
        session = await self._sessions.get_or_raise(session_id)
        self._interview.finish(session)
        await self._sessions.save(session)
        return session
