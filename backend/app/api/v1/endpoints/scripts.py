from typing import Literal

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import get_script_service, get_session_service
from app.schemas.api import ScriptCreate, ScriptSummary, ScriptUpdate, SessionSummary
from app.schemas.script import InterviewScript
from app.services.script_service import ScriptService
from app.services.session_service import SessionService

router = APIRouter(prefix="/scripts")


@router.get("", response_model=list[ScriptSummary])
async def list_scripts(ativos: bool = True, scripts: ScriptService = Depends(get_script_service)):
    return await scripts.list_summaries(only_active=ativos)


@router.post("", response_model=InterviewScript, status_code=status.HTTP_201_CREATED)
async def create_script(payload: ScriptCreate, scripts: ScriptService = Depends(get_script_service)):
    return await scripts.create(payload)


@router.get("/{script_id}", response_model=InterviewScript)
async def get_script(script_id: str, scripts: ScriptService = Depends(get_script_service)):
    return await scripts.get(script_id)


@router.put("/{script_id}", response_model=InterviewScript)
async def update_script(
    script_id: str, payload: ScriptUpdate, scripts: ScriptService = Depends(get_script_service)
):
    return await scripts.update(script_id, payload)


@router.delete("/{script_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_script(script_id: str, scripts: ScriptService = Depends(get_script_service)):
    await scripts.delete(script_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{script_id}/sessions", response_model=list[SessionSummary])
async def list_script_sessions(
    script_id: str,
    status_filter: Literal["em_andamento", "concluida"] | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    sessions: SessionService = Depends(get_session_service),
):
    return await sessions.list_for_script(script_id, status=status_filter, limit=limit)
