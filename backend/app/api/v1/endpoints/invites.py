from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_invite_service
from app.schemas.api import InviteChannel, InvitePublic, InviteSession, InviteStart
from app.schemas.interview import SessionResponse
from app.services.invite_service import InviteService

router = APIRouter(prefix="/convite")


@router.get("/{slug}", response_model=InvitePublic)
async def get_invite(slug: str, invites: InviteService = Depends(get_invite_service)):
    return await invites.get_public(slug)


@router.post("/{slug}/sessao", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_invite_session(
    slug: str,
    payload: InviteStart | None = None,
    invites: InviteService = Depends(get_invite_service),
):
    return await invites.start(slug, payload or InviteStart())


@router.get("/{slug}/sessao/{session_id}", response_model=InviteSession)
async def get_invite_session(
    slug: str, session_id: str, invites: InviteService = Depends(get_invite_service)
):
    """Estado mínimo para retomar a entrevista pública (sem objetivos, perfil nem participante)."""
    return await invites.get_session(slug, session_id)


@router.post("/{slug}/sessao/{session_id}/canal", status_code=status.HTTP_204_NO_CONTENT)
async def set_invite_session_channel(
    slug: str,
    session_id: str,
    payload: InviteChannel,
    invites: InviteService = Depends(get_invite_service),
):
    await invites.set_channel(slug, session_id, payload.canal)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
