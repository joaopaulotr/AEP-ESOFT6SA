"""Checagem determinística de segurança (EV-26), antes e independente do LLM.

Escolhas de projeto:
- Pedido de parar deterministico so em mensagem curta (<= 8 palavras) com frase de parada,
  ou com frase explicita sobre a entrevista em qualquer tamanho; o resto vai ao LLM (risco).
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

_SHORT_STOP_PHRASES = [
    "quero parar",
    "nao quero mais",
    "nao quero continuar",
    "pode parar",
    "vamos parar",
    "chega",
]
# Em mensagem curta, a frase de parada so vale se o resto for so cortesia: assim
# "nao quero mais onibus lotado" ou "quero parar de fumar" seguem para o LLM.
_LEAD_WORDS = {"eu", "ah", "ok", "entao", "olha", "desculpa", "bom", "e"}
_TAIL_WORDS = {"obrigado", "obrigada", "por", "favor", "agora", "aqui", "hoje", "mesmo", "de", "verdade", "pra", "valeu"}
_EXPLICIT_STOP_PATTERNS = [
    r"parar a entrevista",
    r"parar essa entrevista",
    r"encerrar a entrevista",
    r"nao quero continuar a entrevista",
    r"quero parar a entrevista",
    r"para a entrevista",
]
MAX_STOP_WORDS = 8  # frase curta: pedido de parar; mais longa e ambigua vai para o LLM
_DISTRESS_PATTERNS = [
    r"me matar",
    r"tirar minha vida",
    r"me machucar",
    r"nao aguento mais viver",
    r"quero morrer",
    r"acabar com tudo",
    r"suicid",
]

_EXPLICIT_STOP_RE = re.compile("|".join(_EXPLICIT_STOP_PATTERNS))
_DISTRESS_RE = re.compile("|".join(_DISTRESS_PATTERNS))


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def _is_short_stop(normalized: str) -> bool:
    words = re.sub(r"[^a-z0-9 ]", " ", normalized).split()
    if not words or len(words) > MAX_STOP_WORDS:
        return False
    for phrase in _SHORT_STOP_PHRASES:
        size = len(phrase.split())
        for i in range(len(words) - size + 1):
            if words[i : i + size] == phrase.split():
                if set(words[:i]) <= _LEAD_WORDS and set(words[i + size :]) <= _TAIL_WORDS:
                    return True
    return False


def check_safety(text: str) -> Risco:
    normalized = _normalize(text)
    if _DISTRESS_RE.search(normalized):
        return "sofrimento"
    if _EXPLICIT_STOP_RE.search(normalized):
        return "pedido_parar"
    if _is_short_stop(normalized):
        return "pedido_parar"
    return "nenhum"
