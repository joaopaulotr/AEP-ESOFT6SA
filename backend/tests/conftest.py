import json
import os
from types import SimpleNamespace

# LLMClient() constrói o cliente OpenAI real quando nenhum é injetado, e o SDK
# recusa a construção sem credencial. Precisa existir antes de qualquer import de app.
os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

from app.schemas.interview import InterviewState, Turn
from app.services import llm_client as llm_client_module
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


class FakeLLM:
    """Dublê do LLMClient: enfileira respostas e grava os prompts recebidos."""

    def __init__(self) -> None:
        self.responses: list[dict | str] = []
        self.prompts: list[str] = []

    def queue(
        self,
        action: str = "deepen",
        next_utterance: str = "",
        profile_updates: dict | None = None,
        closing_statement: str = "",
    ) -> "FakeLLM":
        return self.queue_payload({
            "action": action,
            "next_utterance": next_utterance,
            "profile_updates": profile_updates or {},
            "closing_statement": closing_statement,
        })

    def queue_payload(self, payload: dict | str) -> "FakeLLM":
        """Enfileira uma resposta crua, para exercitar payloads com chaves faltando."""
        self.responses.append(payload)
        return self

    def _next(self, prompt: str):
        self.prompts.append(prompt)
        if not self.responses:
            raise _UnexpectedCall(
                "Chamada inesperada ao LLM: nenhuma resposta enfileirada. "
                "Use fake_llm.queue(...) antes de exercitar o serviço."
            )
        return self.responses.pop(0)

    def complete_json(self, prompt: str) -> dict:
        return self._next(prompt)

    def complete_text(self, prompt: str) -> str:
        return self._next(prompt)

    @property
    def last_prompt(self) -> str:
        return self.prompts[-1]


class _FakeCompletions:
    def __init__(self) -> None:
        self.responses: list[str] = []
        self.calls: list[dict] = []

    def create(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        if not self.responses:
            raise _UnexpectedCall("Chamada inesperada à OpenAI: nenhuma resposta enfileirada.")
        content = self.responses.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeOpenAI:
    """Dublê do SDK da OpenAI, para exercitar o LLMClient de verdade."""

    def __init__(self) -> None:
        self.completions = _FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)

    def queue_raw(self, content: str) -> "FakeOpenAI":
        self.completions.responses.append(content)
        return self

    def queue_json(self, payload: dict) -> "FakeOpenAI":
        return self.queue_raw(json.dumps(payload))

    @property
    def calls(self) -> list[dict]:
        return self.completions.calls

    @property
    def last_call(self) -> dict:
        return self.calls[-1]


@pytest.fixture(autouse=True)
def _no_real_openai(monkeypatch):
    """Rede fechada: qualquer tentativa de construir o cliente real falha alto."""

    def _explode(*args, **kwargs):
        raise _UnexpectedCall(
            "Tentativa de construir o cliente OpenAI real. Injete um dublê no teste."
        )

    monkeypatch.setattr(llm_client_module, "OpenAI", _explode)


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def service(fake_llm) -> InterviewService:
    return InterviewService(llm_client=fake_llm)


@pytest.fixture
def fake_openai() -> FakeOpenAI:
    return FakeOpenAI()


# --------------------------------------------------------------------------
# Dublês do Mongo
# --------------------------------------------------------------------------


class _FakeCursor:
    def __init__(self, documents: list[dict]) -> None:
        self._documents = documents

    async def to_list(self, length=None) -> list[dict]:
        return self._documents if length is None else self._documents[:length]


class _FakeDeleteResult:
    def __init__(self, deleted_count: int) -> None:
        self.deleted_count = deleted_count


class FakeCollection:
    """Coleção Mongo em memória, com a mesma superfície assíncrona do motor."""

    def __init__(self) -> None:
        self.documents: list[dict] = []
        self.updates: list[tuple[dict, dict]] = []

    def seed(self, *documents: dict) -> "FakeCollection":
        """Insere documentos crus, incluindo o _id que o Mongo devolveria."""
        for index, document in enumerate(documents):
            self.documents.append({"_id": f"oid-{index}", **document})
        return self

    async def insert_one(self, document: dict):
        self.documents.append(dict(document))
        return SimpleNamespace(inserted_id=f"oid-{len(self.documents)}")

    async def find_one(self, query: dict) -> dict | None:
        for document in self.documents:
            if all(document.get(key) == value for key, value in query.items()):
                return dict(document)
        return None

    async def update_one(self, query: dict, update: dict):
        self.updates.append((query, update))
        for document in self.documents:
            if all(document.get(key) == value for key, value in query.items()):
                document.update(update.get("$set", {}))
                return SimpleNamespace(matched_count=1, modified_count=1)
        return SimpleNamespace(matched_count=0, modified_count=0)

    async def delete_one(self, query: dict) -> _FakeDeleteResult:
        for index, document in enumerate(self.documents):
            if all(document.get(key) == value for key, value in query.items()):
                self.documents.pop(index)
                return _FakeDeleteResult(1)
        return _FakeDeleteResult(0)

    def find(self) -> _FakeCursor:
        return _FakeCursor([dict(document) for document in self.documents])


class FakeDB:
    """Banco Mongo em memória: entrega a mesma FakeCollection por nome."""

    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections.setdefault(name, FakeCollection())


@pytest.fixture
def fake_db() -> FakeDB:
    return FakeDB()


@pytest.fixture
def sessions(fake_db) -> FakeCollection:
    """A coleção que o SessionRepository usa por padrão."""
    return fake_db["interview_sessions"]


# --------------------------------------------------------------------------
# Fixtures de domínio
# --------------------------------------------------------------------------


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
