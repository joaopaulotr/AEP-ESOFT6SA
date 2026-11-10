import asyncio
import logging
import re
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import deps
from app.api.v1.endpoints import turns
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.errors import (
    ConflictError,
    CorruptDocumentError,
    FileTooLargeError,
    ImportFileError,
    NotFoundError,
    UnsupportedFileError,
)
from app.providers.base import ProviderError

logger = logging.getLogger(__name__)


async def prepare_database() -> None:
    """Cria os índices das coleções e garante o roteiro seed (idempotente)."""
    for repository in deps.get_repositories():
        await repository.ensure_indexes()
    await deps.get_script_repository().ensure_seed()
    migrated = await deps.get_session_repository().backfill_legacy(
        deps.get_synthesis_repository().import_legacy
    )
    if migrated:
        logger.info("Sessões da v0.1.0 migradas para o modelo multi-coleção: %d", migrated)


SHUTDOWN_DRAIN_SECONDS = 15.0


async def drain_pending_turns(timeout: float = SHUTDOWN_DRAIN_SECONDS) -> int:
    """No desligamento, espera os turnos em andamento gravarem (um restart não pode perder a
    resposta de quem já falou). Devolve quantos ainda não tinham terminado no prazo."""
    pending = set(turns._pending_turns)
    if not pending:
        return 0
    _, still_running = await asyncio.wait(pending, timeout=timeout)
    if still_running:
        logger.warning("Turnos ainda em andamento no desligamento: %d", len(still_running))
    return len(still_running)


def warn_default_frontend_url() -> None:
    """Sem FRONTEND_URL, o link do convite e o QR Code apontam para localhost."""
    if "localhost" in settings.frontend_url or "127.0.0.1" in settings.frontend_url:
        logger.warning(
            "FRONTEND_URL aponta para %s: links de convite e QR Code só funcionam nesta máquina.",
            settings.frontend_url,
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    warn_default_frontend_url()
    await prepare_database()
    yield
    await drain_pending_turns()


app = FastAPI(title="API - ESOFT6SA", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# session_id só é extraído de /session/{id} e /turn/{id}; nenhum outro valor de URL vai pro log.
_SESSION_PATH = re.compile(r"^/api/v1/(?:session|turn)/([^/]+)")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Uma linha de log por requisição: método, rota, status, duração e ids. Sem corpo/query."""
    started = time.perf_counter()
    match = _SESSION_PATH.match(request.url.path)
    extra = {
        "request_id": uuid.uuid4().hex[:12],
        "method": request.method,
        "session_id": match.group(1) if match else None,
    }

    def line(status: int, error_type: str | None = None) -> dict:
        route = request.scope.get("route")  # modelo da rota: ids/tokens do path não vazam
        return {
            **extra,
            "path": getattr(route, "path", "desconhecida"),
            "status": status,
            "error_type": error_type,
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        }

    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error("requisicao", extra=line(500, type(exc).__name__))
        raise
    logger.info("requisicao", extra=line(response.status_code))
    response.headers["X-Request-ID"] = extra["request_id"]
    return response


app.include_router(api_router)


_LOCATIONS = {"body", "query", "path", "header", "cookie"}


def invalid_fields(errors) -> list[str]:
    """Nomes dos campos com erro (sem a origem "body"/"query"), na ordem, sem repetir."""
    fields: list[str] = []
    for error in errors:
        loc = [str(part) for part in error.get("loc", ()) if str(part) not in _LOCATIONS]
        # JSON malformado: o loc traz a posição do byte, que não diz nada a quem lê.
        name = "corpo da requisição" if error.get("type") == "json_invalid" else ".".join(loc)
        name = name or "corpo da requisição"
        if name not in fields:
            fields.append(name)
    return fields


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError):
    """422 em pt-BR com só os nomes dos campos: nunca devolve nem loga o valor enviado."""
    campos = ", ".join(invalid_fields(exc.errors()))
    return JSONResponse(status_code=422, content={"detail": f"Dados inválidos: confira {campos}."})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(CorruptDocumentError)
async def corrupt_document_handler(request: Request, exc: CorruptDocumentError):
    logger.error("%s", exc)  # só a coleção; nunca o conteúdo do documento
    return JSONResponse(status_code=500, content={"detail": "Erro interno ao ler os dados."})


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": exc.message})


@app.exception_handler(FileTooLargeError)
async def file_too_large_handler(request: Request, exc: FileTooLargeError):
    return JSONResponse(status_code=413, content={"detail": exc.message})


@app.exception_handler(UnsupportedFileError)
async def unsupported_file_handler(request: Request, exc: UnsupportedFileError):
    return JSONResponse(status_code=415, content={"detail": exc.message})


@app.exception_handler(ImportFileError)
async def import_file_handler(request: Request, exc: ImportFileError):
    return JSONResponse(status_code=422, content={"detail": exc.message})


@app.exception_handler(ProviderError)
async def provider_error_handler(request: Request, exc: ProviderError):
    return JSONResponse(
        status_code=502,
        content={"detail": "Falha ao se comunicar com o provedor de IA."},
    )


@app.get("/health")
def health():
    return {"status": "ok"}
