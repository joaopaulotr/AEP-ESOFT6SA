import copy
import json
import re

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


_TRANSCRIPT = re.compile(r"<transcricao>(.*?)</transcricao>", re.DOTALL)
_SYNTHESES = re.compile(r"<sinteses>(.*?)</sinteses>", re.DOTALL)


def _fake_session_synthesis(transcript: str) -> dict:
    """Síntese estruturada offline: a citação é a 1ª frase do participante, literal."""
    lines = [
        line.split(":", 1)[1].strip()
        for line in transcript.splitlines()
        if line.startswith("participant:")
    ]
    quotes = []
    if lines:
        first = re.split(r"(?<=[.!?])\s", lines[0], maxsplit=1)[0]
        quotes = [first if len(first) >= 8 else lines[0]]
    return {
        "resumo": FAKE_SYNTHESIS,
        "temas": [{"tema": "Tema simulado", "pontos": ["Ponto simulado (modo offline)."], "citacoes": quotes}],
        "lacunas": [],
    }


def _fake_script_synthesis(inputs_json: str) -> dict:
    """Relatório cruzado offline: reaproveita as citações de entrada."""
    try:
        inputs = json.loads(inputs_json)
    except ValueError:
        inputs = []
    quotes = [
        c for item in inputs for theme in item.get("temas", []) for c in theme.get("citacoes", [])
    ]
    themes = [{"tema": "Tema simulado", "pontos": ["Ponto simulado (modo offline)."], "citacoes": quotes[:3]}]
    return {
        "resumo": FAKE_SYNTHESIS,
        "temas": themes if quotes else [],
        "divergencias": [],
        "lacunas": [],
    }


class FakeLLMProvider(LLMProvider):
    @property
    def model_name(self) -> str:
        return "fake"

    async def complete_json(self, prompt: str) -> dict:
        _report_llm()
        if match := _TRANSCRIPT.search(prompt):
            return _fake_session_synthesis(match.group(1))
        if match := _SYNTHESES.search(prompt):
            return _fake_script_synthesis(match.group(1))
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
