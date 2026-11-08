import io
import json

from openai import AsyncOpenAI, OpenAIError

from app.core.config import settings
from app.providers.base import LLMProvider, ProviderError, SpeechProvider


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

    async def complete_json(self, prompt: str) -> dict:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
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
            )
            return transcription.text
        except OpenAIError as exc:
            raise ProviderError(f"Falha na transcrição de áudio: {exc}") from exc

    async def synthesize(self, text: str) -> bytes:
        try:
            response = await self._client.audio.speech.create(
                model=self._speech_model,
                voice=self._voice,
                input=text,
            )
            return response.content
        except OpenAIError as exc:
            raise ProviderError(f"Falha na síntese de voz: {exc}") from exc
