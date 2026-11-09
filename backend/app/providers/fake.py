import copy

from app.providers.base import LLMProvider, SpeechProvider

FAKE_DECISION: dict = {
    "action": "advance",
    "next_utterance": "",
    "profile_updates": {},
    "closing_statement": "",
}
FAKE_SYNTHESIS = "Síntese gerada em modo offline (provider fake)."
FAKE_TRANSCRIPTION = "Resposta simulada em modo offline."


class FakeLLMProvider(LLMProvider):
    @property
    def model_name(self) -> str:
        return "fake"

    async def complete_json(self, prompt: str) -> dict:
        return copy.deepcopy(FAKE_DECISION)

    async def complete_text(self, prompt: str) -> str:
        return FAKE_SYNTHESIS


class FakeSpeechProvider(SpeechProvider):
    async def transcribe(self, audio: bytes, filename: str = "audio.webm") -> str:
        return FAKE_TRANSCRIPTION

    async def synthesize(self, text: str) -> bytes:
        return b""
