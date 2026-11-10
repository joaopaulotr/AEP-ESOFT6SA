"""Checagem determinística de segurança (EV-26), antes e independente do LLM.

Política conservadora: um falso positivo (encerrar a entrevista sem a pessoa pedir) é
muito pior que um falso negativo, porque o LLM ainda pode devolver risco="pedido_parar".
Por isso o atalho determinístico só dispara em pedido claro:
- Sofrimento vem primeiro: termo de sofrimento sempre retorna "sofrimento" (o
  acolhimento já inclui a opção de encerrar e cita o CVV).
- Pergunta nunca encerra: mensagem que termina em "?" ou tem "quando", "que horas",
  "quanto tempo", "sera que" ou "como" vai para o LLM ("quando vamos parar a entrevista?").
- Fora isso, é pedido de parar se tiver uma frase explícita sobre a entrevista
  ("parar a entrevista", "encerra a entrevista" no início...) ou se for curta
  (<= 8 palavras) com frase de parada cercada só de cortesia ("chega por hoje",
  "por favor, quero parar"). Assim "quero parar de fumar" ou "o ônibus chega às 7h"
  não disparam. O texto é normalizado (sem acento, minúsculas).
"""

import re
import unicodedata
from typing import Literal

Risco = Literal["nenhum", "sofrimento", "pedido_parar"]

MAX_STOP_WORDS = 8

_DISTRESS_RE = re.compile(
    r"me matar|tirar minha vida|me machucar|nao aguento mais viver|quero morrer|acabar com tudo|suicid"
)
_QUESTION_RE = re.compile(r"\?$|\b(quando|que horas|quanto tempo|sera que|como)\b")
_EXPLICIT_STOP_RE = re.compile(
    r"parar a entrevista|parar essa entrevista|encerrar a entrevista|quero parar a entrevista"
    r"|nao quero continuar a entrevista|^(encerra|termina|para) a entrevista"
)

_SHORT_STOP_PHRASES = [p.split() for p in ("quero parar", "nao quero mais", "nao quero continuar", "pode parar", "vamos parar", "chega")]
_LEAD_WORDS = {"eu", "ah", "ok", "entao", "olha", "desculpa", "bom", "e", "por", "favor", "oi", "ola"}
_TAIL_WORDS = {
    "obrigado", "obrigada", "por", "favor", "agora", "aqui", "hoje", "mesmo", "de", "verdade",
    "pra", "valeu", "sim", "tchau", "muito", "tudo", "bem", "ta", "bom", "desculpa", "desculpe",
    "com", "isso", "vez", "falar", "continuar", "conversa", "entrevista",
}


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def _is_short_stop(normalized: str) -> bool:
    words = re.sub(r"[^a-z0-9 ]", " ", normalized).split()
    if not words or len(words) > MAX_STOP_WORDS:
        return False
    for phrase in _SHORT_STOP_PHRASES:
        n = len(phrase)
        for i in range(len(words) - n + 1):
            if words[i : i + n] == phrase and set(words[:i]) <= _LEAD_WORDS and set(words[i + n :]) <= _TAIL_WORDS:
                return True
    return False


def check_safety(text: str) -> Risco:
    normalized = _normalize(text)
    if _DISTRESS_RE.search(normalized):
        return "sofrimento"
    if _QUESTION_RE.search(normalized):
        return "nenhum"
    if _EXPLICIT_STOP_RE.search(normalized) or _is_short_stop(normalized):
        return "pedido_parar"
    return "nenhum"
