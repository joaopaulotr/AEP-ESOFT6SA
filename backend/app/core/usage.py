"""Medidor de uso (EV-62): tokens, segundos de áudio e caracteres de TTS por operação.

Um medidor vive numa ContextVar: cada requisição/tarefa enxerga o seu e os providers
somam nele sem saber de sessão. Fora de `track_usage()` não há medidor e somar é no-op.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from app.core.config import Settings, settings as default_settings


@dataclass
class UsageMeter:
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    stt_seconds: float = 0.0
    tts_chars: int = 0

    def add_llm(self, input_tokens: int | None, output_tokens: int | None) -> None:
        self.llm_input_tokens += max(0, int(input_tokens or 0))
        self.llm_output_tokens += max(0, int(output_tokens or 0))

    def add_stt(self, seconds: float | None) -> None:
        self.stt_seconds += max(0.0, float(seconds or 0.0))

    def add_tts(self, chars: int | None) -> None:
        self.tts_chars += max(0, int(chars or 0))

    @property
    def is_empty(self) -> bool:
        return not (
            self.llm_input_tokens or self.llm_output_tokens or self.stt_seconds or self.tts_chars
        )


_current: ContextVar[UsageMeter | None] = ContextVar("usage_meter", default=None)


def current_meter() -> UsageMeter | None:
    return _current.get()


@contextmanager
def track_usage() -> Iterator[UsageMeter]:
    meter = UsageMeter()
    token = _current.set(meter)
    try:
        yield meter
    finally:
        _current.reset(token)


def estimate_cost(meter: UsageMeter, config: Settings = default_settings) -> float:
    """Custo estimado em USD, com os preços (configuráveis) de `Settings`."""
    cost = (
        meter.llm_input_tokens * config.price_llm_input_per_1m / 1_000_000
        + meter.llm_output_tokens * config.price_llm_output_per_1m / 1_000_000
        + meter.stt_seconds / 60 * config.price_stt_per_minute
        + meter.tts_chars * config.price_tts_per_1m_chars / 1_000_000
    )
    return round(cost, 8)
