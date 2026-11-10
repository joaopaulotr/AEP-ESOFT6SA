"""Checagem determinística de segurança (EV-26), antes e independente do LLM.

Política conservadora: um falso positivo (encerrar a entrevista sem a pessoa pedir) é
muito pior que um falso negativo, porque o LLM ainda decide `risco` em todo turno.
Por isso o atalho determinístico só dispara no que é inequívoco:
- Sofrimento: só frases em 1ª pessoa sem outro sentido ("quero morrer", "vou me matar",
  "penso em suicídio", "tirar minha vida"...), com fronteira de palavra e sem as
  expressões do dia a dia ("me matar de trabalhar", "morrer de rir"). O resto
  ("acabar com tudo", "prevenção ao suicídio") fica para o LLM. Vem primeiro: o
  acolhimento encerra e indica o CVV.
- Pergunta nunca encerra: mensagem que termina em "?" ou tem "quando", "que horas",
  "quanto tempo", "sera que" ou "como" vai para o LLM ("quando vamos parar a entrevista?").
- Fora isso, é pedido de parar se tiver uma frase explícita sobre a entrevista
  ("parar a entrevista", "chega de entrevista"...) ou se for curta (<= 8 palavras) com
  "quero parar", "pode parar" ou "vamos parar" cercada só de cortesia. "Não quero mais",
  "não quero continuar" e "chega" sozinhos são respostas comuns a perguntas de sim/não e
  ficam para o LLM; se o LLM falhar, `mentions_stop` (lista ampla) evita seguir em frente.
O texto é normalizado (sem acento, minúsculas).
"""

import re
import unicodedata
from typing import Literal

Risco = Literal["nenhum", "sofrimento", "pedido_parar"]

MAX_STOP_WORDS = 8

_NOT_DISTRESS = r"(?! de (?:trabalhar|rir|estudar|vergonha|fome|calor|sono|tedio|saudade|medo))"
_DISTRESS_RE = re.compile(
    r"\b(?:"
    rf"quero morrer{_NOT_DISTRESS}"
    rf"|(?:quero|vou) me matar{_NOT_DISTRESS}"
    rf"|(?:penso|pensei|pensando) em (?:me matar{_NOT_DISTRESS}|suicidio|me suicidar|tirar minha (?:propria )?vida)"
    r"|tirar minha (?:propria )?vida"
    r"|quero me suicidar"
    r")\b"
)
_QUESTION_RE = re.compile(r"\?$|\b(quando|que horas|quanto tempo|sera que|como)\b")
_EXPLICIT_STOP_RE = re.compile(
    r"parar a entrevista|parar essa entrevista|encerrar a entrevista|quero parar a entrevista"
    r"|nao quero continuar a entrevista|chega de entrevista"
    r"|nao quero mais (?:fazer )?(?:a |essa )?entrevista"
    r"|^(encerra|termina|para) a entrevista"
)

_SHORT_STOP_PHRASES = [p.split() for p in ("quero parar", "pode parar", "vamos parar")]
# Lista ampla: só decide quando o LLM falhou (ver `mentions_stop`). Vale em qualquer
# ponto da mensagem: sem o LLM, "Não quero mais responder" ou "Já deu, chega" encerram.
_BROAD_STOP_PHRASES = (
    "quero parar", "pode parar", "vamos parar", "chega", "ja deu", "nao quero mais",
    "nao quero continuar", "quero encerrar", "pode encerrar", "quero sair",
    "nao quero responder", "para por favor",
)
_BROAD_STOP_RE = re.compile(r"\b(?:" + "|".join(re.escape(p) for p in _BROAD_STOP_PHRASES) + r")\b")
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


def _is_short_stop(normalized: str, phrases: list[list[str]] = _SHORT_STOP_PHRASES) -> bool:
    words = re.sub(r"[^a-z0-9 ]", " ", normalized).split()
    if not words or len(words) > MAX_STOP_WORDS:
        return False
    for phrase in phrases:
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


def mentions_stop(text: str) -> bool:
    """Lista ampla de parada, para quando o LLM falhou e não pode decidir: na dúvida entre
    seguir com a próxima pergunta ou respeitar um possível pedido de parar, para."""
    normalized = _normalize(text)
    if _QUESTION_RE.search(normalized):
        return False
    words = " ".join(re.sub(r"[^a-z0-9 ]", " ", normalized).split())  # sem pontuação
    return bool(_EXPLICIT_STOP_RE.search(normalized) or _BROAD_STOP_RE.search(words))
