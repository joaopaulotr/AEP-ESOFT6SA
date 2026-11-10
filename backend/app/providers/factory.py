from app.core.config import Settings
from app.providers.base import LLMProvider, SpeechProvider
from app.providers.fake import FakeLLMProvider, FakeSpeechProvider
from app.providers.openai_provider import OpenAILLMProvider, OpenAISpeechProvider


def build_llm_provider(settings: Settings) -> LLMProvider:
    match settings.llm_provider:
        case "fake":
            return FakeLLMProvider()
        case "openai":
            return OpenAILLMProvider(model=settings.llm_model)


def build_speech_provider(settings: Settings) -> SpeechProvider:
    match settings.llm_provider:
        case "fake":
            return FakeSpeechProvider()
        case "openai":
            return OpenAISpeechProvider(speech_model=settings.speech_model)
