from app.core.errors import ConflictError, NotFoundError
from app.core.links import build_invite_link
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.script_repository import ScriptRepository
from app.schemas.api import InviteLink, InvitePublic, InviteStart
from app.schemas.interview import SessionResponse
from app.schemas.participant import Participant
from app.schemas.script import InterviewScript
from app.services.session_service import SessionService

INVALID_INVITE_MESSAGE = "Convite inválido ou encerrado."


class InviteService:
    """Convite público: a pessoa entra pelo link, sem login, e cai numa sessão."""

    def __init__(
        self,
        scripts: ScriptRepository,
        participants: ParticipantRepository,
        sessions: SessionService,
    ) -> None:
        self._scripts = scripts
        self._participants = participants
        self._sessions = sessions

    async def _active_script(self, slug: str) -> InterviewScript:
        script = await self._scripts.get_by_slug(slug)
        if script is None or not script.ativo:
            raise NotFoundError(INVALID_INVITE_MESSAGE)
        return script

    async def get_public(self, slug: str) -> InvitePublic:
        script = await self._active_script(slug)
        return InvitePublic(
            slug=script.slug_convite,
            titulo=script.titulo,
            tema=script.tema,
            descricao=script.descricao,
            persona=script.persona,
            perguntas_total=len(script.perguntas),
            link=build_invite_link(script.slug_convite),
        )

    async def start(self, slug: str, payload: InviteStart) -> SessionResponse:
        script = await self._active_script(slug)
        participant = Participant(**payload.model_dump())
        await self._participants.create(participant)
        try:
            return await self._sessions.open(script.script_id, participant.participant_id)
        except ConflictError:
            await self._participants.delete(participant.participant_id)
            raise NotFoundError(INVALID_INVITE_MESSAGE) from None

    async def link_for_script(self, script_id: str) -> InviteLink:
        script = await self._scripts.get_or_raise(script_id)
        return InviteLink(slug=script.slug_convite, link=build_invite_link(script.slug_convite))
