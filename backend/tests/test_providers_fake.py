import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.providers.base import LLMProvider, SpeechProvider
from app.providers.factory import build_llm_provider, build_speech_provider
from app.providers.fake import (
    FAKE_DECISION,
    FAKE_SYNTHESIS,
    FAKE_TRANSCRIPTION,
    FakeLLMProvider,
    FakeSpeechProvider,
)

pytestmark = pytest.mark.anyio


async def test_fake_llm_returns_the_fixed_advance_decision():
    assert await FakeLLMProvider().complete_json("qualquer") == FAKE_DECISION
    assert FAKE_DECISION["action"] == "advance"


async def test_fake_llm_returns_a_copy_each_time():
    provider = FakeLLMProvider()
    first = await provider.complete_json("p")
    first["action"] = "finish"
    first["profile_updates"]["x"] = 1
    again = await provider.complete_json("p")
    assert again["action"] == "advance"
    assert again["profile_updates"] == {}


async def test_fake_llm_text_is_the_offline_synthesis():
    assert await FakeLLMProvider().complete_text("p") == FAKE_SYNTHESIS


async def test_fake_speech_transcribes_to_the_fixed_text():
    assert await FakeSpeechProvider().transcribe(b"abc", "a.webm") == FAKE_TRANSCRIPTION


async def test_fake_speech_synthesizes_empty_audio():
    assert await FakeSpeechProvider().synthesize("olá") == b""


def test_providers_are_abstract():
    with pytest.raises(TypeError):
        LLMProvider()
    with pytest.raises(TypeError):
        SpeechProvider()


def test_factory_builds_fake_providers():
    s = Settings(llm_provider="fake")
    assert isinstance(build_llm_provider(s), FakeLLMProvider)
    assert isinstance(build_speech_provider(s), FakeSpeechProvider)


def test_settings_rejects_unknown_provider():
    with pytest.raises(ValidationError):
        Settings(llm_provider="gemini")
