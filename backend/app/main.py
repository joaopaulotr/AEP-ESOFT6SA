from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import deps
from app.api.v1.endpoints import session, turns, voice
from app.core.errors import ConflictError, NotFoundError
from app.providers.base import ProviderError


async def prepare_database() -> None:
    """Cria os índices das coleções e garante o roteiro seed (idempotente)."""
    for repository in deps.get_repositories():
        await repository.ensure_indexes()
    await deps.get_script_repository().ensure_seed()


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

app.include_router(session.router)
app.include_router(turns.router)
app.include_router(voice.router)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


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
