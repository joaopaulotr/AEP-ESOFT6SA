from fastapi import APIRouter, Depends, status

from app.api.deps import get_invite_service
from app.schemas.api import InvitePublic, InviteStart
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
