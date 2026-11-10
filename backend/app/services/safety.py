"""Checagem determinística de segurança (EV-26), antes e independente do LLM.

Escolhas de projeto:
- O texto é normalizado (sem acento, minúsculas) e comparado com frases inteiras,
  conservadoras. Pedido de parar exige a forma de pedido em 1ª pessoa/imperativo
  ("quero parar", "pode parar", "vamos parar"): "parar o ônibus" ou "parar de fumar"
  NÃO disparam, porque não casam com nenhuma dessas frases. "chega" só vale como
  palavra inteira ("chegamos", "chegada" não disparam).
- Precedência: segurança primeiro. Se houver termo de sofrimento, o resultado é
  "sofrimento" mesmo que a pessoa também peça para parar: o acolhimento já inclui a
  opção de encerrar e cita o CVV. Só sem termos de sofrimento vale "pedido_parar".
"""

import re
import unicodedata
from typing import Literal

Risco = Literal["nenhum", "sofrimento", "pedido_parar"]

_STOP_PATTERNS = [
    r"quero parar",
    r"nao quero mais",
    r"nao quero continuar",
    r"pode parar",
    r"vamos parar",
    r"\bchega\b",
    r"para a entrevista",
    r"encerrar a entrevista",
]
_DISTRESS_PATTERNS = [
    r"me matar",
    r"tirar minha vida",
    r"me machucar",
    r"nao aguento mais viver",
    r"quero morrer",
    r"acabar com tudo",
    r"suicid",
]

_STOP_RE = re.compile("|".join(_STOP_PATTERNS))
_DISTRESS_RE = re.compile("|".join(_DISTRESS_PATTERNS))


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def check_safety(text: str) -> Risco:
    normalized = _normalize(text)
    if _DISTRESS_RE.search(normalized):
        return "sofrimento"
    if _STOP_RE.search(normalized):
        return "pedido_parar"
    return "nenhum"
