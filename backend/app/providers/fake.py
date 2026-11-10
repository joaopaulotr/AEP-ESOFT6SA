import copy

from app.core.usage import current_meter
from app.providers.base import LLMProvider, SpeechProvider, Tom

FAKE_DECISION: dict = {
    "action": "advance",
    "next_utterance": "",
    "profile_updates": {},
    "closing_statement": "",
    "probe_tipo": None,
    "risco": "nenhum",
    "reconhecimento": "",
}
FAKE_INPUT_TOKENS = 100
FAKE_OUTPUT_TOKENS = 30
FAKE_STT_SECONDS = 2.0
FAKE_SYNTHESIS = "Síntese gerada em modo offline (provider fake)."
FAKE_TRANSCRIPTION = "Resposta simulada em modo offline."


def _report_llm() -> None:
    if (meter := current_meter()) is not None:
        meter.add_llm(FAKE_INPUT_TOKENS, FAKE_OUTPUT_TOKENS)


class FakeLLMProvider(LLMProvider):
    @property
    def model_name(self) -> str:
        return "fake"

    async def complete_json(self, prompt: str) -> dict:
        _report_llm()
        return copy.deepcopy(FAKE_DECISION)

    async def complete_text(self, prompt: str) -> str:
        _report_llm()
        return FAKE_SYNTHESIS


class FakeSpeechProvider(SpeechProvider):
    async def transcribe(self, audio: bytes, filename: str = "audio.webm") -> str:
        if (meter := current_meter()) is not None:
            meter.add_stt(FAKE_STT_SECONDS)
        return FAKE_TRANSCRIPTION

    async def synthesize(self, text: str, tom: Tom | None = None) -> bytes:
        if (meter := current_meter()) is not None:
            meter.add_tts(len(text))
        return b""
