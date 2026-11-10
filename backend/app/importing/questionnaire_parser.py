"""Transforma o texto de um questionário em rascunho de roteiro (LLM + fallback heurístico)."""

import re
from datetime import datetime, timezone
from pathlib import PurePath

from pydantic import BaseModel, ValidationError

from app.core.errors import EmptyQuestionnaireError
from app.prompts.import_prompts import IMPORT_PROMPT
from app.providers.base import LLMProvider, ProviderError
from app.schemas.api import DraftQuestion, ScriptDraft
from app.schemas.script import ScriptOrigin

MAX_TEXT_CHARS = 20_000
MAX_QUESTIONS = 20

FALLBACK_WARNING = "A IA não conseguiu ler o arquivo; usei a leitura automática. Revise as perguntas."
TRUNCATED_WARNING = "O arquivo é grande; usei só o começo."
CAPPED_WARNING = f"Mantive só as {MAX_QUESTIONS} primeiras perguntas."

_PREFIX = re.compile(r"^\s*(?:\d+\s*[.)]|[-•*])\s+")


class _LLMQuestion(BaseModel):
    texto: str
    objetivo: str = ""


class _LLMDraft(BaseModel):
    titulo: str = ""
    tema: str = ""
    descricao: str = ""
    perguntas: list[_LLMQuestion] = []


def _origin(filename: str) -> ScriptOrigin:
    return ScriptOrigin(tipo="upload", arquivo=filename, extraido_em=datetime.now(timezone.utc))


def _title_from(filename: str) -> str:
    return PurePath(filename).stem.strip() or "Roteiro importado"


def _dedupe(questions: list[DraftQuestion]) -> list[DraftQuestion]:
    seen: set[str] = set()
    unique = []
    for question in questions:
        key = " ".join(question.texto.lower().split())
        if key and key not in seen:
            seen.add(key)
            unique.append(question)
    return unique


def heuristic_parse(text: str, filename: str) -> ScriptDraft:
    """Leitura sem IA: linhas com '?' ou numeradas (1. / 1)); tira numeração e marcadores."""
    found = []
    for line in text.splitlines():
        stripped = line.strip()
        numbered = re.match(r"^\d+\s*[.)]\s+\S", stripped) is not None
        if not stripped or not (stripped.endswith("?") or numbered):
            continue
        clean = _PREFIX.sub("", stripped).strip()
        if clean:
            found.append(DraftQuestion(texto=clean))
    questions = _dedupe(found)
    avisos = []
    if len(questions) > MAX_QUESTIONS:
        questions = questions[:MAX_QUESTIONS]
        avisos.append(CAPPED_WARNING)
    return ScriptDraft(
        titulo=_title_from(filename), perguntas=questions, origem=_origin(filename), avisos=avisos
    )


class QuestionnaireParser:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def parse(self, text: str, filename: str) -> ScriptDraft:
        avisos: list[str] = []
        if len(text) > MAX_TEXT_CHARS:
            text = text[:MAX_TEXT_CHARS]
            avisos.append(TRUNCATED_WARNING)
        draft = await self._parse_with_llm(text, filename)
        if draft is None:
            draft = heuristic_parse(text, filename)
            avisos.append(FALLBACK_WARNING)
        if not draft.perguntas:
            raise EmptyQuestionnaireError("Não encontrei perguntas no arquivo.")
        draft.avisos = avisos + [w for w in draft.avisos if w not in avisos]
        return draft

    async def _parse_with_llm(self, text: str, filename: str) -> ScriptDraft | None:
        try:
            payload = await self._llm.complete_json(IMPORT_PROMPT.format(texto=text))
            parsed = _LLMDraft.model_validate(payload)
        except (ProviderError, ValidationError):
            return None
        questions = _dedupe(
            [
                DraftQuestion(texto=q.texto.strip(), objetivo=q.objetivo.strip())
                for q in parsed.perguntas
                if q.texto.strip()
            ]
        )
        if not questions:
            return None
        avisos = []
        if len(questions) > MAX_QUESTIONS:
            questions = questions[:MAX_QUESTIONS]
            avisos.append(CAPPED_WARNING)
        return ScriptDraft(
            titulo=parsed.titulo.strip() or _title_from(filename),
            tema=parsed.tema.strip(),
            descricao=parsed.descricao.strip(),
            perguntas=questions,
            origem=_origin(filename),
            avisos=avisos,
        )
