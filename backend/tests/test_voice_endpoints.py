import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_speech_provider
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
    r = client.post("/voice/transcricao", files={"file": ("r.webm", b"\x01\x02", "audio/webm")})
    assert r.status_code == 200 and r.json() == {"texto": speech.transcription}
    assert speech.transcribe_calls == [(b"\x01\x02", "r.webm")]


def test_empty_audio_returns_400_without_calling_the_provider(client, speech):
    r = client.post("/voice/transcricao", files={"file": ("r.webm", b"", "audio/webm")})
    assert r.status_code == 400 and r.json() == {"detail": "Áudio vazio."}
    assert speech.transcribe_calls == []


def test_speech_returns_mpeg_audio(client, speech):
    r = client.post("/voice/fala", json={"texto": "olá"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
    assert r.content == speech.audio


def test_speech_rejects_empty_text(client):
    assert client.post("/voice/fala", json={"texto": ""}).status_code == 422


def test_provider_failure_returns_502(client, speech):
    speech.fail_with(ProviderError("fora"))
    r = client.post("/voice/fala", json={"texto": "olá"})
    assert r.status_code == 502


def test_transcription_provider_failure_returns_502(client, speech):
    speech.fail_with(ProviderError("fora"))
    r = client.post("/voice/transcricao", files={"file": ("r.webm", b"\x01", "audio/webm")})
    assert r.status_code == 502
