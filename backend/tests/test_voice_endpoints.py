import openai
import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.deps import get_speech_provider
from app.core.config import settings
from app.providers import openai_provider
from app.main import app
from app.providers.base import ProviderError, SpeechProvider


class RecordingSpeech(SpeechProvider):
    def __init__(self) -> None:
        self.transcription = "texto transcrito"
        self.audio = b"mp3-bytes"
        self.transcribe_calls: list[tuple[bytes, str]] = []
        self._error: Exception | None = None

    def fail_with(self, exc: Exception) -> None:
        self._error = exc

    def _maybe_fail(self) -> None:
        if self._error is not None:
            exc, self._error = self._error, None
            raise exc

    async def transcribe(self, audio: bytes, filename: str = "audio.webm") -> str:
        self._maybe_fail()
        self.transcribe_calls.append((audio, filename))
        return self.transcription

    async def synthesize(self, text: str) -> bytes:
        self._maybe_fail()
        return self.audio


@pytest.fixture
def speech() -> RecordingSpeech:
    return RecordingSpeech()


@pytest.fixture
def client(speech):
    app.dependency_overrides[get_speech_provider] = lambda: speech
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_transcription_returns_the_text(client, speech):
    r = client.post("/api/v1/voice/transcricao", files={"file": ("r.webm", b"\x01\x02", "audio/webm")})
    assert r.status_code == 200 and r.json() == {"texto": speech.transcription}
    assert speech.transcribe_calls == [(b"\x01\x02", "r.webm")]


def test_empty_audio_returns_400_without_calling_the_provider(client, speech):
    r = client.post("/api/v1/voice/transcricao", files={"file": ("r.webm", b"", "audio/webm")})
    assert r.status_code == 400 and r.json() == {"detail": "Áudio vazio."}
    assert speech.transcribe_calls == []


def test_speech_returns_mpeg_audio(client, speech):
    r = client.post("/api/v1/voice/fala", json={"texto": "olá"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
    assert r.content == speech.audio


def test_speech_rejects_empty_text(client):
    assert client.post("/api/v1/voice/fala", json={"texto": ""}).status_code == 422


def test_provider_failure_returns_502(client, speech):
    speech.fail_with(ProviderError("fora"))
    r = client.post("/api/v1/voice/fala", json={"texto": "olá"})
    assert r.status_code == 502
    assert r.json() == {"detail": "Falha ao se comunicar com o provedor de IA."}


def test_transcription_provider_failure_returns_502(client, speech):
    speech.fail_with(ProviderError("fora"))
    r = client.post("/api/v1/voice/transcricao", files={"file": ("r.webm", b"\x01", "audio/webm")})
    assert r.status_code == 502
    assert r.json() == {"detail": "Falha ao se comunicar com o provedor de IA."}


def test_audio_over_the_limit_returns_413_without_calling_the_provider(client, speech, monkeypatch):
    monkeypatch.setattr(settings, "max_audio_bytes", 4)
    r = client.post("/api/v1/voice/transcricao", files={"file": ("r.webm", b"12345", "audio/webm")})
    assert r.status_code == 413 and r.json() == {"detail": "Áudio maior que o permitido."}
    assert speech.transcribe_calls == []


def test_audio_exactly_at_the_limit_is_accepted(client, speech, monkeypatch):
    monkeypatch.setattr(settings, "max_audio_bytes", 4)
    r = client.post("/api/v1/voice/transcricao", files={"file": ("r.webm", b"1234", "audio/webm")})
    assert r.status_code == 200


@pytest.mark.parametrize("texto", ["", "   \n"])
def test_blank_transcription_returns_400(client, speech, texto):
    speech.transcription = texto
    r = client.post("/api/v1/voice/transcricao", files={"file": ("r.webm", b"\x01", "audio/webm")})
    assert r.status_code == 400 and r.json() == {"detail": "Não foi possível entender o áudio."}


def test_unconfigured_openai_provider_returns_502_not_500(monkeypatch):
    def _boom(**kwargs):
        raise openai.OpenAIError("sem chave")

    deps.reset_dependencies()
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(openai_provider, "AsyncOpenAI", _boom)
    try:
        with TestClient(app) as test_client:
            r = test_client.post("/api/v1/voice/fala", json={"texto": "olá"})
    finally:
        deps.reset_dependencies()
    assert r.status_code == 502
    assert r.json() == {"detail": "Falha ao se comunicar com o provedor de IA."}
