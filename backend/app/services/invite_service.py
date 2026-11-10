from io import BytesIO

import segno

from app.core.errors import ConflictError, NotFoundError
from app.core.links import build_invite_link
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.script_repository import ScriptRepository
from app.schemas.api import InviteLink, InvitePublic, InviteSession, InviteStart, PublicTurn
from app.schemas.interview import InterviewState, SessionResponse
from app.schemas.participant import Participant
from app.schemas.script import InterviewScript
from app.services.interview_graph import ended_in_welcome
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
        except Exception as exc:
            # Qualquer falha ao abrir a sessão: o participante não fica órfão.
            await self._participants.delete(participant.participant_id)
            if isinstance(exc, (ConflictError, NotFoundError)):
                raise NotFoundError(INVALID_INVITE_MESSAGE) from None
            raise

    async def _session_of_invite(self, slug: str, session_id: str) -> tuple[InterviewScript, InterviewState]:
        """A sessão só é acessível pelo slug do roteiro a que pertence. Vale também para
        roteiro desativado no meio da entrevista (quem já começou pode recarregar a tela)."""
        script = await self._scripts.get_by_slug(slug)
        if script is None:
            raise NotFoundError(INVALID_INVITE_MESSAGE)
        try:
            session = await self._sessions.get(session_id)
        except NotFoundError:
            raise NotFoundError(INVALID_INVITE_MESSAGE) from None
        if session.script_id != script.script_id:
            raise NotFoundError(INVALID_INVITE_MESSAGE)
        return script, session

    async def get_session(self, slug: str, session_id: str) -> InviteSession:
        script, session = await self._session_of_invite(slug, session_id)
        return InviteSession(
            session_id=session.session_id,
            titulo=script.titulo,
            perguntas_total=len(script.perguntas),
            current_index=session.current_index,
            finished=session.finished,
            acolhimento=ended_in_welcome(session),
            persona=script.persona,
            conversation=[PublicTurn(role=t.role, text=t.text) for t in session.conversation],
        )

    async def set_channel(self, slug: str, session_id: str, canal: str) -> None:
        """Troca voz <-> texto no meio da entrevista: o painel conta o canal do participante."""
        _, session = await self._session_of_invite(slug, session_id)
        if session.participant_id is None:
            return
        participant = await self._participants.get(session.participant_id)
        if participant is None or participant.canal == canal:
            return
        participant.canal = canal
        await self._participants.save(participant)

    async def link_for_script(self, script_id: str) -> InviteLink:
        script = await self._scripts.get_or_raise(script_id)
        return InviteLink(slug=script.slug_convite, link=build_invite_link(script.slug_convite))

    async def qrcode_svg(self, script_id: str) -> bytes:
        invite = await self.link_for_script(script_id)
        buffer = BytesIO()
        segno.make(invite.link, error="m").save(buffer, kind="svg", scale=6, border=2)
        return buffer.getvalue()
