import json

import httpx
import openai
import pytest

from app.core.config import Settings
from app.providers import openai_provider
from app.providers.base import ProviderError
from app.providers.factory import build_llm_provider, build_speech_provider
from app.providers.openai_provider import OpenAILLMProvider, OpenAISpeechProvider

pytestmark = pytest.mark.anyio


def _conn_error() -> openai.APIConnectionError:
    return openai.APIConnectionError(request=httpx.Request("POST", "http://x"))


class TestCompleteJson:
    async def test_parses_the_json_payload(self, fake_async_openai):
        fake_async_openai.queue_json({"action": "advance", "next_utterance": "Vamos lá."})

        result = await OpenAILLMProvider(client=fake_async_openai).complete_json("um prompt")

        assert result == {"action": "advance", "next_utterance": "Vamos lá."}

    async def test_asks_the_model_for_a_json_object(self, fake_async_openai):
        fake_async_openai.queue_json({"action": "deepen"})

        await OpenAILLMProvider(client=fake_async_openai).complete_json("um prompt")

        call = fake_async_openai.last_call
        assert call["response_format"] == {"type": "json_object"}
        assert call["model"] == "gpt-4o-mini"
        assert call["messages"] == [{"role": "user", "content": "um prompt"}]

    async def test_invalid_json_raises_provider_error(self, fake_async_openai):
        fake_async_openai.queue_raw("isto não é json")

        with pytest.raises(ProviderError) as info:
            await OpenAILLMProvider(client=fake_async_openai).complete_json("p")
        assert isinstance(info.value.__cause__, json.JSONDecodeError)

    async def test_none_content_raises_provider_error(self, fake_async_openai):
        fake_async_openai.queue_raw(None)

        with pytest.raises(ProviderError, match="vazi"):
            await OpenAILLMProvider(client=fake_async_openai).complete_json("p")

    async def test_non_object_json_raises_provider_error(self, fake_async_openai):
        fake_async_openai.queue_raw("[1, 2]")

        with pytest.raises(ProviderError, match="objeto"):
            await OpenAILLMProvider(client=fake_async_openai).complete_json("p")

    async def test_api_failure_raises_provider_error(self, fake_async_openai):
        fake_async_openai.fail_next(_conn_error())

        with pytest.raises(ProviderError):
            await OpenAILLMProvider(client=fake_async_openai).complete_text("p")

    async def test_json_api_failure_raises_provider_error(self, fake_async_openai):
        fake_async_openai.fail_next(_conn_error())

        with pytest.raises(ProviderError):
            await OpenAILLMProvider(client=fake_async_openai).complete_json("p")


class TestCompleteText:
    async def test_none_content_raises_provider_error(self, fake_async_openai):
        fake_async_openai.queue_raw(None)

        with pytest.raises(ProviderError, match="vazi"):
            await OpenAILLMProvider(client=fake_async_openai).complete_text("p")

    async def test_returns_the_raw_content(self, fake_async_openai):
        fake_async_openai.queue_raw("uma síntese qualquer")

        provider = OpenAILLMProvider(client=fake_async_openai)
        assert await provider.complete_text("um prompt") == "uma síntese qualquer"

    async def test_does_not_force_a_response_format(self, fake_async_openai):
        fake_async_openai.queue_raw("texto")

        await OpenAILLMProvider(client=fake_async_openai).complete_text("um prompt")

        assert "response_format" not in fake_async_openai.last_call
        assert fake_async_openai.last_call["messages"] == [
            {"role": "user", "content": "um prompt"}
        ]


class TestModelSelection:
    async def test_defaults_to_gpt_4o_mini(self, fake_async_openai):
        fake_async_openai.queue_raw("texto")

        await OpenAILLMProvider(client=fake_async_openai).complete_text("um prompt")

        assert fake_async_openai.last_call["model"] == "gpt-4o-mini"

    async def test_honours_a_custom_model(self, fake_async_openai):
        fake_async_openai.queue_raw("texto")

        provider = OpenAILLMProvider(client=fake_async_openai, model="gpt-4o")
        await provider.complete_text("um prompt")

        assert fake_async_openai.last_call["model"] == "gpt-4o"
        assert provider.model == "gpt-4o"
        assert provider.model_name == "gpt-4o"  # gravado em syntheses.modelo

    def test_model_is_read_only(self, fake_async_openai):
        provider = OpenAILLMProvider(client=fake_async_openai)
        with pytest.raises(AttributeError):
            provider.model = "outro"


class TestNoRealApiCalls:
    def test_default_construction_never_reaches_the_network(self):
        with pytest.raises(AssertionError, match="cliente OpenAI real"):
            OpenAILLMProvider()


async def test_transcribe_sends_portuguese_and_domain_prompt(fake_async_openai):
    fake_async_openai.queue_transcription("eu trabalho à noite")
    text = await OpenAISpeechProvider(client=fake_async_openai).transcribe(b"\x00\x01", "r.webm")
    call = fake_async_openai.last_transcription_call
    assert text == "eu trabalho à noite"
    assert call["model"] == "whisper-1" and call["language"] == "pt" and call["temperature"] == 0
    assert call["response_format"] == "verbose_json"
    assert call["file"].name == "r.webm"
    assert call["prompt"] == "Entrevista qualitativa em português sobre o dia a dia de trabalho."


async def test_synthesize_returns_audio_bytes(fake_async_openai):
    fake_async_openai.queue_speech(b"MP3DATA")
    audio = await OpenAISpeechProvider(client=fake_async_openai).synthesize("olá")
    call = fake_async_openai.last_speech_call
    assert audio == b"MP3DATA"
    assert call == {"model": "gpt-4o-mini-tts", "voice": "alloy", "input": "olá"}


@pytest.mark.parametrize(
    "tom, esperado",
    [
        ("acolhedor", "Fale em português do Brasil, com calma e calor humano, em ritmo de conversa, com pausas naturais nas vírgulas."),
        ("neutro", "Fale em português do Brasil, de forma clara e tranquila, em ritmo de conversa."),
        ("formal", "Fale em português do Brasil, de forma cordial e profissional, com ritmo pausado."),
    ],
)
async def test_synthesize_with_tom_sends_portuguese_instructions(fake_async_openai, tom, esperado):
    fake_async_openai.queue_speech(b"MP3")
    await OpenAISpeechProvider(client=fake_async_openai).synthesize("olá", tom)
    assert fake_async_openai.last_speech_call["instructions"] == esperado


@pytest.mark.parametrize("call", ["transcribe", "synthesize"])
async def test_speech_api_failure_raises_provider_error(fake_async_openai, call):
    fake_async_openai.fail_next(_conn_error())
    provider = OpenAISpeechProvider(client=fake_async_openai)
    with pytest.raises(ProviderError):
        await (provider.transcribe(b"\x01") if call == "transcribe" else provider.synthesize("olá"))


def test_factory_builds_openai_providers_with_configured_model(monkeypatch, fake_async_openai):
    # o autouse bloqueia AsyncOpenAI; aqui ele é trocado por um construtor que devolve o dublê
    monkeypatch.setattr(openai_provider, "AsyncOpenAI", lambda **kwargs: fake_async_openai)
    s = Settings(llm_provider="openai", llm_model="gpt-4o")
    provider = build_llm_provider(s)
    assert isinstance(provider, OpenAILLMProvider) and provider.model == "gpt-4o"
    assert isinstance(build_speech_provider(s), OpenAISpeechProvider)


class TestClientConstruction:
    @pytest.mark.parametrize("cls", [OpenAILLMProvider, OpenAISpeechProvider])
    def test_builds_the_client_with_timeout_and_no_sdk_retries(self, monkeypatch, cls, fake_async_openai):
        captured: dict = {}

        def _build(**kwargs):
            captured.update(kwargs)
            return fake_async_openai

        monkeypatch.setattr(openai_provider, "AsyncOpenAI", _build)
        monkeypatch.setattr(openai_provider.settings, "openai_api_key", "sk-x")

        cls()

        assert captured == {
            "api_key": "sk-x",
            "timeout": openai_provider.settings.llm_timeout_seconds,
            "max_retries": 0,
        }
        assert openai_provider.settings.llm_timeout_seconds == 20.0

    @pytest.mark.parametrize("cls", [OpenAILLMProvider, OpenAISpeechProvider])
    def test_client_construction_failure_becomes_provider_error(self, monkeypatch, cls):
        def _boom(**kwargs):
            raise openai.OpenAIError("sem chave")

        monkeypatch.setattr(openai_provider, "AsyncOpenAI", _boom)

        with pytest.raises(ProviderError, match="não configurado") as info:
            cls()
        assert isinstance(info.value.__cause__, openai.OpenAIError)


async def test_truncated_json_is_an_invalid_json_error(fake_async_openai):
    from app.providers.base import InvalidJSONError

    fake_async_openai.queue_raw('{"resumo": "x')
    with pytest.raises(InvalidJSONError):
        await OpenAILLMProvider(client=fake_async_openai).complete_json("p")


@pytest.mark.parametrize("model", ["tts-1", "tts-1-hd"])
async def test_older_speech_models_do_not_get_instructions(fake_async_openai, model):
    fake_async_openai.queue_speech(b"MP3")
    await OpenAISpeechProvider(client=fake_async_openai, speech_model=model).synthesize("olá", "acolhedor")
    call = fake_async_openai.last_speech_call
    assert call["model"] == model and "instructions" not in call


def test_factory_uses_the_configured_speech_model(monkeypatch, fake_async_openai):
    monkeypatch.setattr(openai_provider, "AsyncOpenAI", lambda **kwargs: fake_async_openai)
    provider = build_speech_provider(Settings(llm_provider="openai", speech_model="tts-1"))
    assert provider._speech_model == "tts-1" and not provider.supports_instructions
