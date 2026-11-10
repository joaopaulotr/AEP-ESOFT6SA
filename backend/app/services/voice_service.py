from app.core.usage import record_usage_safely, track_usage
from app.providers.base import SpeechProvider, Tom
from app.repositories.session_repository import SessionRepository


class VoiceService:
    """Transcrição e fala com o consumo medido e somado na sessão informada (EV-62).

    Sessão desconhecida (ou nenhuma) não falha a voz: o uso só deixa de ser atribuído."""

    def __init__(self, speech: SpeechProvider, sessions: SessionRepository) -> None:
        self._speech = speech
        self._sessions = sessions

    async def _attribute(self, session_id: str | None, meter) -> None:
        if session_id:
            await record_usage_safely(self._sessions, session_id, meter)

    async def transcribe(self, audio: bytes, filename: str, session_id: str | None = None) -> str:
        with track_usage() as meter:
            try:
                return await self._speech.transcribe(audio, filename)
            finally:
                await self._attribute(session_id, meter)

    async def synthesize(self, texto: str, tom: Tom | None, session_id: str | None = None) -> bytes:
        with track_usage() as meter:
            try:
                return await self._speech.synthesize(texto, tom)
            finally:
                await self._attribute(session_id, meter)
