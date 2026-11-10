import json
import os
from types import SimpleNamespace

# Defesa: se algum código construir um cliente OpenAI sem injeção, o SDK recusa
# a construção sem credencial. Precisa existir antes de qualquer import de app.
os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.api import deps
from app.db import mongodb
from app.db.seed import generalist_script
from app.providers import openai_provider
from app.providers.base import LLMProvider
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.script_repository import ScriptRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.synthesis_repository import SynthesisRepository
from app.schemas.interview import InterviewState, Turn
from app.schemas.script import InterviewScript
from app.services.interview_service import InterviewService


class _UnexpectedCall(AssertionError):
    pass


# --------------------------------------------------------------------------
# Suporte a testes assíncronos (plugin do anyio, já instalado via starlette)
# --------------------------------------------------------------------------


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# --------------------------------------------------------------------------
# Dublês de LLM
# --------------------------------------------------------------------------


class FakeLLM(LLMProvider):
    """Dublê do LLMProvider: enfileira respostas e grava os prompts recebidos."""

    def __init__(self) -> None:
        self.responses: list = []
        self.prompts: list[str] = []

    def queue_error(self, exc: Exception) -> "FakeLLM":
        """A próxima chamada (json ou texto) levanta exc."""
        self.responses.append(exc)
        return self

    def queue(
        self,
        action: str = "deepen",
        next_utterance: str | None = None,
        profile_updates: dict | None = None,
        closing_statement: str = "",
    ) -> "FakeLLM":
        if next_utterance is None:  # deepen exige fala; os demais não
            next_utterance = "Me conta mais." if action == "deepen" else ""
        return self.queue_payload(
            {
                "action": action,
                "next_utterance": next_utterance,
                "profile_updates": profile_updates or {},
                "closing_statement": closing_statement,
            }
        )

    def queue_payload(self, payload) -> "FakeLLM":
        """Enfileira uma resposta crua (dict ou str), para exercitar payloads parciais."""
        self.responses.append(payload)
        return self

    def _next(self, prompt: str):
        self.prompts.append(prompt)
        if not self.responses:
            raise _UnexpectedCall(
                "Chamada inesperada ao LLM: nenhuma resposta enfileirada. "
                "Use fake_llm.queue(...) antes de exercitar o serviço."
            )
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def complete_json(self, prompt: str) -> dict:
        return self._next(prompt)

    async def complete_text(self, prompt: str) -> str:
        return self._next(prompt)

    @property
    def last_prompt(self) -> str:
        return self.prompts[-1]


class _AsyncFakeCompletions:
    def __init__(self, owner: "FakeAsyncOpenAI") -> None:
        self._owner = owner
        self.responses: list[str] = []
        self.calls: list[dict] = []
        self.prompt_tokens = 100
        self.completion_tokens = 30

    async def create(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        self._owner._raise_if_failing()
        if not self.responses:
            raise _UnexpectedCall("Chamada inesperada à OpenAI: nenhuma resposta enfileirada.")
        content = self.responses.pop(0)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(
                prompt_tokens=self.prompt_tokens, completion_tokens=self.completion_tokens
            ),
        )


class _AsyncFakeTranscriptions:
    def __init__(self, owner: "FakeAsyncOpenAI") -> None:
        self._owner = owner
        self.responses: list[str] = []
        self.calls: list[dict] = []
        self.duration = 3.5

    async def create(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        self._owner._raise_if_failing()
        if not self.responses:
            raise _UnexpectedCall("Chamada inesperada à transcrição: nada enfileirado.")
        return SimpleNamespace(text=self.responses.pop(0), duration=self.duration)


class _AsyncFakeSpeech:
    def __init__(self, owner: "FakeAsyncOpenAI") -> None:
        self._owner = owner
        self.responses: list[bytes] = []
        self.calls: list[dict] = []

    async def create(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        self._owner._raise_if_failing()
        if not self.responses:
            raise _UnexpectedCall("Chamada inesperada à síntese de fala: nada enfileirado.")
        return SimpleNamespace(content=self.responses.pop(0))


class FakeAsyncOpenAI:
    """Dublê async do SDK da OpenAI (AsyncOpenAI), para exercitar os providers."""

    def __init__(self) -> None:
        self._failure: Exception | None = None
        self.completions = _AsyncFakeCompletions(self)
        self.transcriptions = _AsyncFakeTranscriptions(self)
        self.speech = _AsyncFakeSpeech(self)
        self.chat = SimpleNamespace(completions=self.completions)
        self.audio = SimpleNamespace(transcriptions=self.transcriptions, speech=self.speech)

    def _raise_if_failing(self) -> None:
        if self._failure is not None:
            failure, self._failure = self._failure, None
            raise failure

    def fail_next(self, exc: Exception) -> "FakeAsyncOpenAI":
        """A próxima chamada, de qualquer endpoint, levanta exc."""
        self._failure = exc
        return self

    def queue_raw(self, content: str) -> "FakeAsyncOpenAI":
        self.completions.responses.append(content)
        return self

    def queue_json(self, payload: dict) -> "FakeAsyncOpenAI":
        return self.queue_raw(json.dumps(payload))

    def queue_transcription(self, text: str) -> "FakeAsyncOpenAI":
        self.transcriptions.responses.append(text)
        return self

    def queue_speech(self, content: bytes) -> "FakeAsyncOpenAI":
        self.speech.responses.append(content)
        return self

    @property
    def calls(self) -> list[dict]:
        return self.completions.calls

    @property
    def last_call(self) -> dict:
        return self.calls[-1]

    @property
    def last_transcription_call(self) -> dict:
        return self.transcriptions.calls[-1]

    @property
    def last_speech_call(self) -> dict:
        return self.speech.calls[-1]


@pytest.fixture(autouse=True)
def _no_real_openai(monkeypatch):
    """Rede fechada: qualquer tentativa de construir o cliente real falha alto."""

    def _explode(*args, **kwargs):
        raise _UnexpectedCall(
            "Tentativa de construir o cliente OpenAI real. Injete um dublê no teste."
        )

    monkeypatch.setattr(openai_provider, "AsyncOpenAI", _explode)


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def service(fake_llm) -> InterviewService:
    return InterviewService(llm=fake_llm)


@pytest.fixture
def fake_async_openai() -> FakeAsyncOpenAI:
    return FakeAsyncOpenAI()


# --------------------------------------------------------------------------
# Banco em memória (mongomock-motor): executa filtros, índices e aggregate
# --------------------------------------------------------------------------


def memory_db():
    """Banco MongoDB em memória, isolado por chamada."""
    return AsyncMongoMockClient(tz_aware=True)["aep_test"]


@pytest.fixture
def fake_db():
    return memory_db()


@pytest.fixture(autouse=True)
def _app_uses_memory_db(monkeypatch, fake_db):
    """O app (deps + lifespan) nunca fala com o Mongo real nos testes."""
    monkeypatch.setattr(mongodb, "db", fake_db)
    deps.reset_dependencies()
    yield
    deps.reset_dependencies()


@pytest.fixture
def sessions(fake_db):
    """A coleção crua que o SessionRepository usa."""
    return fake_db["interview_sessions"]


@pytest.fixture
def script_repository(fake_db) -> ScriptRepository:
    return ScriptRepository(fake_db)


@pytest.fixture
def participant_repository(fake_db) -> ParticipantRepository:
    return ParticipantRepository(fake_db)


@pytest.fixture
def session_repository(fake_db) -> SessionRepository:
    return SessionRepository(fake_db)


@pytest.fixture
def synthesis_repository(fake_db) -> SynthesisRepository:
    return SynthesisRepository(fake_db)


# --------------------------------------------------------------------------
# Fixtures de domínio
# --------------------------------------------------------------------------


@pytest.fixture
def script() -> InterviewScript:
    """Roteiro seed (as 4 perguntas da v0.1.0)."""
    return generalist_script()


@pytest.fixture
def state() -> InterviewState:
    return InterviewState()


@pytest.fixture
def turns():
    def _make(*texts: str) -> list[Turn]:
        return [
            Turn(role="participant" if index % 2 else "interviewer", text=text)
            for index, text in enumerate(texts)
        ]

    return _make
