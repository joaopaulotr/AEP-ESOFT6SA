"""Conferência de citações: só entra na síntese o que é trecho literal da fala (RK-10)."""

import re
from collections.abc import Iterable

from app.schemas.synthesis import Citation

_QUOTES = "\"'“”‘’«»`"


def normalize(text: str) -> str:
    """Espaços colapsados, sem bordas e sem diferença de caixa."""
    return re.sub(r"\s+", " ", text).strip().casefold()


def strip_quotes(text: str) -> str:
    """Remove aspas que o LLM costuma colocar em volta da citação."""
    return text.strip().strip(_QUOTES).strip()


def filter_literal_citations(citacoes: Iterable[str], participant_texts: Iterable[str]) -> list[str]:
    """Mantém só as citações que são trecho literal de UMA fala do participante
    (após normalizar espaços e caixa). Devolve o texto sem aspas, como o LLM o escreveu."""
    haystacks = [normalize(text) for text in participant_texts]
    kept: list[str] = []
    for raw in citacoes:
        if not isinstance(raw, str):
            continue
        quote = strip_quotes(raw)
        needle = normalize(quote)
        if needle and any(needle in haystack for haystack in haystacks):
            kept.append(quote)
    return kept


def filter_known_citations(citacoes: Iterable[Citation], known: Iterable[Citation]) -> list[Citation]:
    """Mantém só as citações iguais (mesma sessão, mesmo texto normalizado) a uma de entrada."""
    allowed = {(c.session_id, normalize(c.texto)) for c in known}
    kept: list[Citation] = []
    for citation in citacoes:
        quote = strip_quotes(citation.texto)
        if quote and (citation.session_id, normalize(quote)) in allowed:
            kept.append(Citation(texto=quote, session_id=citation.session_id))
    return kept
