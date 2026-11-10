from collections.abc import Callable, Coroutine
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from app.api.deps import (
    get_import_service,
    get_invite_service,
    get_script_service,
    get_session_service,
    get_synthesis_service,
)
from app.core.config import settings
from app.schemas.api import InviteLink, ScriptCreate, ScriptDashboard, ScriptDraft, ScriptSummary, ScriptUpdate, SessionSummary
from app.schemas.script import InterviewScript
from app.schemas.synthesis import Synthesis
from app.services.import_service import ImportService, too_large_message
from app.services.invite_service import InviteService
from app.services.script_service import ScriptService
from app.services.session_service import SessionService
from app.services.synthesis_service import SynthesisService

# Folga para os cabeçalhos do multipart (nome do campo, nome do arquivo, boundary).
MULTIPART_OVERHEAD_BYTES = 64 * 1024
LENGTH_REQUIRED_MESSAGE = "Envie o arquivo com o tamanho informado."


class UploadLimitRoute(APIRoute):
    """Confere o Content-Length ANTES do parse do multipart: sem tamanho numérico (upload
    chunked) -> 411; maior que o limite + 64 KB -> 413. O navegador sempre informa o tamanho
    de um FormData. Uma dependência não serve: o FastAPI lê o formulário (e o Starlette grava
    em disco) antes de resolvê-las. O servidor (h11) não aceita corpo maior que o declarado."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def limited(request: Request) -> Response:
            length = request.headers.get("content-length", "")
            if not length.isdigit():
                return JSONResponse(status_code=411, content={"detail": LENGTH_REQUIRED_MESSAGE})
            limit = settings.max_upload_bytes + MULTIPART_OVERHEAD_BYTES
            if int(length) > limit:
                return JSONResponse(status_code=413, content={"detail": too_large_message()})
            return await handler(request)

        return limited


router = APIRouter(prefix="/scripts")
upload_router = APIRouter(prefix="/scripts", route_class=UploadLimitRoute)


@router.get("", response_model=list[ScriptSummary])
async def list_scripts(ativos: bool = True, scripts: ScriptService = Depends(get_script_service)):
    return await scripts.list_summaries(only_active=ativos)


@router.post("", response_model=InterviewScript, status_code=status.HTTP_201_CREATED)
async def create_script(payload: ScriptCreate, scripts: ScriptService = Depends(get_script_service)):
    return await scripts.create(payload)


@upload_router.post("/upload", response_model=ScriptDraft)
async def upload_script(
    file: UploadFile = File(...), imports: ImportService = Depends(get_import_service)
):
    """Lê o questionário enviado e devolve um rascunho; não salva nada.

    Corpo maior que o limite + 64 KB é recusado antes do parse (UploadLimitRoute); o
    arquivo em si é conferido de novo aqui, sem nunca ler mais que o limite + 1 byte."""
    data = await file.read(settings.max_upload_bytes + 1)  # nunca lê o arquivo inteiro
    return await imports.build_draft(file.filename or "", data)


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


@router.get("/{script_id}/painel", response_model=ScriptDashboard)
async def get_script_dashboard(script_id: str, sessions: SessionService = Depends(get_session_service)):
    return await sessions.dashboard(script_id)


@router.get("/{script_id}/convite", response_model=InviteLink)
async def get_script_invite(script_id: str, invites: InviteService = Depends(get_invite_service)):
    return await invites.link_for_script(script_id)


@router.get("/{script_id}/qrcode.svg")
async def get_script_qrcode(script_id: str, invites: InviteService = Depends(get_invite_service)):
    return Response(content=await invites.qrcode_svg(script_id), media_type="image/svg+xml")


@router.post("/{script_id}/sintese", response_model=Synthesis)
async def synthesize_script(
    script_id: str,
    refresh: bool = False,
    synthesis: SynthesisService = Depends(get_synthesis_service),
):
    """Relatório cruzado do roteiro; devolve o salvo, e `?refresh=true` gera de novo (paga o LLM)."""
    return await synthesis.synthesize_script(script_id, refresh=refresh)


@router.get("/{script_id}/sintese", response_model=Synthesis)
async def get_script_synthesis(
    script_id: str, synthesis: SynthesisService = Depends(get_synthesis_service)
):
    return await synthesis.get_script(script_id)
