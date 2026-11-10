from fastapi import APIRouter

from app.api.v1.endpoints import invites, participants, scripts, session, turns, voice

API_PREFIX = "/api/v1"

api_router = APIRouter(prefix=API_PREFIX)
api_router.include_router(scripts.router)
api_router.include_router(participants.router)
api_router.include_router(session.router)
api_router.include_router(turns.router)
api_router.include_router(voice.router)
api_router.include_router(invites.router)
