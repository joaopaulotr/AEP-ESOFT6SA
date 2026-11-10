from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.errors import FileTooLargeError
from app.importing.extractors import extractor_for
from app.importing.questionnaire_parser import QuestionnaireParser
from app.schemas.api import ScriptDraft


def format_megabytes(size: int) -> str:
    """2097152 -> "2 MB"; 524288 -> "0,5 MB" (pt-BR)."""
    value = round(size / (1024 * 1024), 1)
    return f"{value:g}".replace(".", ",") + " MB"


def too_large_message() -> str:
    return f"Arquivo maior que {format_megabytes(settings.max_upload_bytes)}."


class ImportService:
    """Arquivo enviado -> rascunho de roteiro. O app nunca grava nem loga o arquivo.

    A rota recusa pelo Content-Length antes do parse do multipart; o que passa desse corte
    (no máximo o limite + 64 KB) ainda pode ir para um temporário do Starlette."""

    def __init__(self, parser: QuestionnaireParser) -> None:
        self._parser = parser

    async def build_draft(self, filename: str, data: bytes) -> ScriptDraft:
        if len(data) > settings.max_upload_bytes:
            raise FileTooLargeError(too_large_message())
        extractor = extractor_for(filename)  # 415 antes de ler o conteúdo
        text = await run_in_threadpool(extractor.extract, data)  # fora do event loop
        return await self._parser.parse(text, filename)
