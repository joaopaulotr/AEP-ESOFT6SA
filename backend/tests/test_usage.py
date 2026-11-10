"""Medidor de uso, custo estimado e métricas por entrevista (EV-62)."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.core.usage import UsageMeter, current_meter, estimate_cost, track_usage
from app.main import app
from app.providers.fake import FakeLLMProvider, FakeSpeechProvider
from app.providers.openai_provider import OpenAILLMProvider, OpenAISpeechProvider
from app.schemas.interview import InterviewState

API = "/api/v1"


# -- medidor ---------------------------------------------------------------


def test_no_meter_outside_track_usage():
    assert current_meter() is None


def test_track_usage_installs_and_removes_the_meter():
    with track_usage() as meter:
        assert current_meter() is meter
    assert current_meter() is None


@pytest.mark.anyio
async def test_meters_are_isolated_between_concurrent_tasks():
    async def work(tokens: int) -> UsageMeter:
        with track_usage() as meter:
            await asyncio.sleep(0)
            current_meter().add_llm(tokens, tokens)
            await asyncio.sleep(0)
            return meter

    first, second = await asyncio.gather(work(10), work(500))
    assert (first.llm_input_tokens, second.llm_input_tokens) == (10, 500)


def test_estimate_cost_uses_configured_prices():
    meter = UsageMeter(
        llm_input_tokens=1_000_000, llm_output_tokens=1_000_000, stt_seconds=60, tts_chars=1_000_000
    )
    assert estimate_cost(meter, Settings()) == pytest.approx(0.15 + 0.60 + 0.006 + 15.0)
    assert estimate_cost(UsageMeter(), Settings()) == 0


def test_defaults_match_the_documented_prices():
    s = Settings()
    assert (s.price_llm_input_per_1m, s.price_llm_output_per_1m) == (0.15, 0.60)
    assert (s.price_stt_per_minute, s.price_tts_per_1m_chars) == (0.006, 15.0)


# -- providers -------------------------------------------------------------


@pytest.mark.anyio
async def test_openai_providers_report_usage(fake_async_openai):
    fake_async_openai.queue_json({"a": 1}).queue_raw("texto").queue_transcription("oi").queue_speech(b"x")
    llm = OpenAILLMProvider(client=fake_async_openai)
    speech = OpenAISpeechProvider(client=fake_async_openai)
    with track_usage() as meter:
        await llm.complete_json("p")
        await llm.complete_text("p")
        await speech.transcribe(b"\x01")
        await speech.synthesize("olá!")
    assert (meter.llm_input_tokens, meter.llm_output_tokens) == (200, 60)
    assert meter.stt_seconds == 3.5 and meter.tts_chars == 4


@pytest.mark.anyio
async def test_providers_without_meter_do_nothing(fake_async_openai):
    fake_async_openai.queue_raw("texto")
    assert await OpenAILLMProvider(client=fake_async_openai).complete_text("p") == "texto"


@pytest.mark.anyio
async def test_fake_providers_report_small_fixed_usage():
    with track_usage() as meter:
        await FakeLLMProvider().complete_json("p")
        await FakeSpeechProvider().transcribe(b"x")
        await FakeSpeechProvider().synthesize("abc")
    assert (meter.llm_input_tokens, meter.llm_output_tokens) == (100, 30)
    assert meter.stt_seconds == 2.0 and meter.tts_chars == 3


# -- métricas na sessão ----------------------------------------------------


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "fake")  # providers fake (deps recriadas por teste)
    with TestClient(app) as test_client:
        yield test_client


def _metricas(client, session_id) -> dict:
    return client.get(f"{API}/session/{session_id}").json()["metricas"]


def _open(client) -> str:
    return client.post(f"{API}/session").json()["session_id"]


def test_turn_adds_usage_and_cost_to_the_session(client):
    sid = _open(client)
    client.post(f"{API}/turn/{sid}", json={"texto": "resposta"})
    m = _metricas(client, sid)
    assert (m["llm_input_tokens"], m["llm_output_tokens"], m["tokens"]) == (100, 30, 130)
    expected = estimate_cost(UsageMeter(llm_input_tokens=100, llm_output_tokens=30))
    assert m["custo_usd"] == pytest.approx(expected)
    client.post(f"{API}/turn/{sid}", json={"texto": "outra"})
    assert _metricas(client, sid)["tokens"] == 260


def test_streaming_turn_also_adds_usage(client):
    sid = _open(client)
    client.post(f"{API}/turn/{sid}/stream", json={"texto": "resposta"})
    assert _metricas(client, sid)["tokens"] == 130


def test_metrics_update_does_not_bump_versao(client):
    sid = _open(client)
    before = client.get(f"{API}/session/{sid}").json()["versao"]
    assert client.post(f"{API}/turn/{sid}", json={"texto": "x"}).status_code == 200
    after = client.get(f"{API}/session/{sid}").json()["versao"]
    assert after == before + 1  # só o save do turno; o $inc não soma versão


@pytest.mark.anyio
async def test_add_metrics_is_atomic_and_keeps_versao(session_repository):
    state = InterviewState()
    await session_repository.create(state)
    meter = UsageMeter(llm_input_tokens=5, llm_output_tokens=2, stt_seconds=1.5, tts_chars=7)
    assert await session_repository.add_metrics(state.session_id, meter, 0.25)
    assert await session_repository.add_metrics(state.session_id, meter, 0.25)
    saved = await session_repository.get(state.session_id)
    assert saved.versao == state.versao
    assert saved.metricas.tokens == 14 and saved.metricas.segundos_audio == 3.0
    assert saved.metricas.tts_chars == 14 and saved.metricas.custo_usd == 0.5
    assert not await session_repository.add_metrics("inexistente", meter, 0.1)


@pytest.mark.anyio
async def test_save_does_not_overwrite_metrics(session_repository):
    state = InterviewState()
    await session_repository.create(state)
    await session_repository.add_metrics(state.session_id, UsageMeter(llm_input_tokens=9), 0.1)
    await session_repository.save(state)  # cópia velha, metricas zeradas
    assert (await session_repository.get(state.session_id)).metricas.llm_input_tokens == 9


def test_synthesis_adds_usage(client):
    sid = _open(client)
    client.post(f"{API}/turn/{sid}", json={"texto": "resposta"})
    client.post(f"{API}/session/{sid}/finish")
    before = _metricas(client, sid)["tokens"]
    assert client.post(f"{API}/session/{sid}/synthesis").status_code == 200
    assert _metricas(client, sid)["tokens"] == before + 130


def test_voice_usage_is_attributed_to_the_session(client):
    sid = _open(client)
    files = {"file": ("r.webm", b"\x01", "audio/webm")}
    assert client.post(f"{API}/voice/transcricao?session_id={sid}", files=files).status_code == 200
    client.post(f"{API}/voice/fala?session_id={sid}", json={"texto": "olá"})
    m = _metricas(client, sid)
    assert m["stt_seconds"] == 2.0 and m["segundos_audio"] == 2.0 and m["tts_chars"] == 3
    assert m["custo_usd"] > 0


def test_voice_with_unknown_session_still_works(client):
    files = {"file": ("r.webm", b"\x01", "audio/webm")}
    assert client.post(f"{API}/voice/transcricao?session_id=nao-existe", files=files).status_code == 200
    assert client.post(f"{API}/voice/fala?session_id=nao-existe", json={"texto": "olá"}).status_code == 200


def test_voice_without_session_id_is_unchanged(client):
    assert client.post(f"{API}/voice/fala", json={"texto": "olá"}).status_code == 200
