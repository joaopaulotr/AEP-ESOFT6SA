import io

from openai import OpenAI

from app.core.config import settings


class VoiceService:
    def __init__(
        self,
        client: OpenAI | None = None,
        transcription_model: str = "whisper-1",
        speech_model: str = "gpt-4o-mini-tts",
        voice: str = "alloy",
    ) -> None:
        self._client = client or OpenAI(api_key=settings.openai_api_key or None)
        self._transcription_model = transcription_model
        self._speech_model = speech_model
        self._voice = voice

    def transcrever(self, audio: bytes, filename: str = "audio.webm") -> str:
        buffer = io.BytesIO(audio)
        buffer.name = filename
        transcription = self._client.audio.transcriptions.create(
            model=self._transcription_model,
            file=buffer,
        )
        return transcription.text

    def sintetizar_fala(self, texto: str) -> bytes:
        with self._client.audio.speech.with_streaming_response.create(
            model=self._speech_model,
            voice=self._voice,
            input=texto,
        ) as response:
            return response.read()
