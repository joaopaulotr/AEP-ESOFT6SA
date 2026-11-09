from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Falha de provedor externo (rede, API, resposta inválida)."""


class LLMProvider(ABC):
    @abstractmethod
    async def complete_json(self, prompt: str) -> dict: ...

    @abstractmethod
    async def complete_text(self, prompt: str) -> str: ...


class SpeechProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, filename: str = "audio.webm") -> str: ...

    @abstractmethod
    async def synthesize(self, text: str) -> bytes: ...
