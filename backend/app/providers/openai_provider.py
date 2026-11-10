import io
import json

from openai import AsyncOpenAI, OpenAIError

from app.core.config import settings
from app.core.usage import current_meter
from app.providers.base import LLMProvider, ProviderError, SpeechProvider, Tom


TOM_INSTRUCTIONS: dict[str, str] = {
    "acolhedor": (
        "Fale em português do Brasil, com calma e calor humano, em ritmo de conversa, "
        "com pausas naturais nas vírgulas."
    ),
    "neutro": "Fale em português do Brasil, de forma clara e tranquila, em ritmo de conversa.",
    "formal": "Fale em português do Brasil, de forma cordial e profissional, com ritmo pausado.",
}


def _report_llm_usage(response) -> None:
    meter = current_meter()
    usage = getattr(response, "usage", None)
    if meter is not None and usage is not None:
        meter.add_llm(getattr(usage, "prompt_tokens", 0), getattr(usage, "completion_tokens", 0))


def _build_client() -> AsyncOpenAI:
    # max_retries=0: o retry fica no InterviewService, com o timeout total sob controle.
    try:
        return AsyncOpenAI(
            api_key=settings.openai_api_key or None,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
        )
    except OpenAIError as exc:
        raise ProviderError("Provedor de IA não configurado.") from exc


class OpenAILLMProvider(LLMProvider):
    def __init__(self, client: AsyncOpenAI | None = None, model: str = "gpt-4o-mini") -> None:
        self._client = client or _build_client()
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @property
    def model_name(self) -> str:
        return self.model

    async def complete_json(self, prompt: str) -> dict:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            _report_llm_usage(response)
            content = response.choices[0].message.content
        except OpenAIError as exc:
            raise ProviderError(f"Falha no provedor de LLM: {exc}") from exc
        if content is None:
            raise ProviderError("O provedor de LLM devolveu uma resposta vazia.")
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Falha no provedor de LLM: {exc}") from exc
        if not isinstance(payload, dict):
            raise ProviderError("O provedor de LLM não devolveu um objeto JSON.")
        return payload

    async def complete_text(self, prompt: str) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
            )
            _report_llm_usage(response)
            content = response.choices[0].message.content
        except OpenAIError as exc:
            raise ProviderError(f"Falha no provedor de LLM: {exc}") from exc
        if content is None:
            raise ProviderError("O provedor de LLM devolveu uma resposta vazia.")
        return content


class OpenAISpeechProvider(SpeechProvider):
    def __init__(
        self,
        client: AsyncOpenAI | None = None,
        transcription_model: str = "whisper-1",
        speech_model: str = "gpt-4o-mini-tts",
        voice: str = "alloy",
    ) -> None:
        self._client = client or _build_client()
        self._transcription_model = transcription_model
        self._speech_model = speech_model
        self._voice = voice

    async def transcribe(self, audio: bytes, filename: str = "audio.webm") -> str:
        buffer = io.BytesIO(audio)
        buffer.name = filename
        try:
            transcription = await self._client.audio.transcriptions.create(
                model=self._transcription_model,
                file=buffer,
                language="pt",
                temperature=0,
                prompt="Entrevista qualitativa em português sobre o dia a dia de trabalho.",
                response_format="verbose_json",
            )
            if (meter := current_meter()) is not None:
                meter.add_stt(getattr(transcription, "duration", 0))
            return transcription.text
        except OpenAIError as exc:
            raise ProviderError(f"Falha na transcrição de áudio: {exc}") from exc

    async def synthesize(self, text: str, tom: Tom | None = None) -> bytes:
        options = {"instructions": TOM_INSTRUCTIONS[tom]} if tom else {}
        try:
            response = await self._client.audio.speech.create(
                model=self._speech_model,
                voice=self._voice,
                input=text,
                **options,
            )
            if (meter := current_meter()) is not None:
                meter.add_tts(len(text))
            return response.content
        except OpenAIError as exc:
            raise ProviderError(f"Falha na síntese de voz: {exc}") from exc
