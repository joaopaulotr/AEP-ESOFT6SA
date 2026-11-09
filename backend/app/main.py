import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import deps
from app.api.v1.router import api_router
from app.core.errors import ConflictError, CorruptDocumentError, NotFoundError
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


@asynccontextmanager
async def lifespan(_: FastAPI):
    await prepare_database()
    yield


app = FastAPI(title="API - ESOFT6SA", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


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


@app.exception_handler(ProviderError)
async def provider_error_handler(request: Request, exc: ProviderError):
    return JSONResponse(
        status_code=502,
        content={"detail": "Falha ao se comunicar com o provedor de IA."},
    )


@app.get("/health")
def health():
    return {"status": "ok"}
