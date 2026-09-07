import json
import os
from types import SimpleNamespace

# interview_service constrói o cliente OpenAI no import do módulo, e o SDK
# recusa a construção sem credencial. Precisa existir antes de qualquer import de app.
os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

from app.schemas.interview import InterviewState, Turn
from app.services import interview_service


class _FakeCompletions:
    def __init__(self) -> None:
        self.responses: list[str] = []
        self.calls: list[dict] = []

    def create(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError(
                "Chamada inesperada à OpenAI: nenhuma resposta enfileirada. "
                "Use fake_openai.queue(...) antes de exercitar o serviço."
            )
        content = self.responses.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeOpenAI:
    """Dublê do cliente OpenAI: enfileira respostas e grava as chamadas recebidas."""

    def __init__(self) -> None:
        self.completions = _FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)

    def queue(
        self,
        action: str = "deepen",
        next_utterance: str = "",
        profile_updates: dict | None = None,
        closing_statement: str = "",
    ) -> "FakeOpenAI":
        return self.queue_payload({
            "action": action,
            "next_utterance": next_utterance,
            "profile_updates": profile_updates or {},
            "closing_statement": closing_statement,
        })

    def queue_payload(self, payload: dict) -> "FakeOpenAI":
        """Enfileira um JSON cru, para exercitar respostas com chaves faltando."""
        self.responses.append(json.dumps(payload))
        return self

    @property
    def responses(self) -> list[str]:
        return self.completions.responses

    @property
    def calls(self) -> list[dict]:
        return self.completions.calls

    @property
    def last_prompt(self) -> str:
        return self.calls[-1]["messages"][0]["content"]


@pytest.fixture(autouse=True)
def fake_openai(monkeypatch) -> FakeOpenAI:
    """Substitui o cliente global em todos os testes: nenhuma chamada real de rede."""
    fake = FakeOpenAI()
    monkeypatch.setattr(interview_service, "client", fake)
    return fake


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
