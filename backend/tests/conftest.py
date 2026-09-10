import json
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import pytest

from app.schemas.interview import InterviewState, Turn
from app.services.interview_service import InterviewService


class FakeLLMClient:
    """Dublê do LLMClient: enfileira respostas e grava os prompts recebidos."""

    def __init__(self) -> None:
        self.responses: list[str] = []
        self.prompts: list[str] = []

    def queue(
        self,
        action: str = "deepen",
        next_utterance: str = "",
        profile_updates: dict | None = None,
        closing_statement: str = "",
    ) -> "FakeLLMClient":
        return self.queue_payload(
            {
                "action": action,
                "next_utterance": next_utterance,
                "profile_updates": profile_updates or {},
                "closing_statement": closing_statement,
            }
        )

    def queue_payload(self, payload: dict) -> "FakeLLMClient":
        self.responses.append(json.dumps(payload))
        return self

    def queue_text(self, text: str) -> "FakeLLMClient":
        self.responses.append(text)
        return self

    def _next(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.responses:
            raise AssertionError(
                "Chamada inesperada ao LLM: nenhuma resposta enfileirada. "
                "Use fake_llm.queue(...) antes de exercitar o serviço."
            )
        return self.responses.pop(0)

    def complete_json(self, prompt: str) -> dict:
        return json.loads(self._next(prompt))

    def complete_text(self, prompt: str) -> str:
        return self._next(prompt)

    @property
    def last_prompt(self) -> str:
        return self.prompts[-1]


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def interview_service(fake_llm: FakeLLMClient) -> InterviewService:
    return InterviewService(llm_client=fake_llm)


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
