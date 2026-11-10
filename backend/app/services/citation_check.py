"""Conferência de citações: só entra na síntese o que é trecho literal da fala (RK-10)."""

import re
from collections.abc import Iterable

from app.schemas.synthesis import Citation

MIN_CITATION_CHARS = 8
_QUOTES = "\"'“”‘’«»`"
_MARKER_TAGS = re.compile(r"</?\s*(?:transcricao|sinteses)\s*>", re.IGNORECASE)


def sanitize(text: str) -> str:
    """Tira as marcas que delimitam os dados nos prompts, para a fala do participante
    não conseguir fechar o bloco e se passar por instrução."""
    return _MARKER_TAGS.sub("", text)


def normalize(text: str) -> str:
    """Espaços colapsados, sem bordas e sem diferença de caixa."""
    return re.sub(r"\s+", " ", text).strip().casefold()


def strip_quotes(text: str) -> str:
    """Remove aspas que o LLM costuma colocar em volta da citação."""
    return text.strip().strip(_QUOTES).strip()


def _original_slice(quote: str, texts: list[str]) -> str | None:
    """Trecho ORIGINAL (caixa e espaços da fala) que corresponde à citação, ou None."""
    words = quote.split()
    if not words:
        return None
    pattern = re.compile(r"\s+".join(re.escape(word) for word in words), re.IGNORECASE)
    for text in texts:
        if match := pattern.search(text):
            return match.group(0)
    return None


def filter_literal_citations(citacoes: Iterable[str], participant_texts: Iterable[str]) -> list[str]:
    """Mantém só as citações que são trecho literal de UMA fala do participante (espaços e
    caixa normalizados) e têm ao menos 8 caracteres. Devolve o trecho original da fala."""
    texts = list(participant_texts)
    kept: list[str] = []
    for raw in citacoes:
        if not isinstance(raw, str):
            continue
        quote = strip_quotes(raw)
        if len(normalize(quote)) < MIN_CITATION_CHARS:
            continue
        if (original := _original_slice(quote, texts)) is not None:
            kept.append(original)
    return kept


def filter_known_citations(citacoes: Iterable[Citation], known: Iterable[Citation]) -> list[Citation]:
    """Mantém só as citações iguais (mesma sessão, texto normalizado) a uma de entrada,
    guardando o texto da citação de entrada (original), não o do LLM."""
    allowed = {(c.session_id, normalize(c.texto)): c for c in known}
    kept: list[Citation] = []
    for citation in citacoes:
        source = allowed.get((citation.session_id, normalize(strip_quotes(citation.texto))))
        if source is not None and len(normalize(source.texto)) >= MIN_CITATION_CHARS:
            kept.append(Citation(texto=source.texto, session_id=source.session_id))
    return kept
