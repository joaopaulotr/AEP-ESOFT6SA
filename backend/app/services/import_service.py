from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.errors import FileTooLargeError
from app.importing.extractors import extractor_for
from app.importing.questionnaire_parser import QuestionnaireParser
from app.schemas.api import ScriptDraft

TOO_LARGE_MESSAGE = "Arquivo maior que 2 MB."


class ImportService:
    """Arquivo enviado -> rascunho de roteiro. O app nunca grava nem loga o arquivo (o Starlette pode usar temporário para uploads grandes)."""

    def __init__(self, parser: QuestionnaireParser) -> None:
        self._parser = parser

    async def build_draft(self, filename: str, data: bytes) -> ScriptDraft:
        if len(data) > settings.max_upload_bytes:
            raise FileTooLargeError(TOO_LARGE_MESSAGE)
        extractor = extractor_for(filename)  # 415 antes de ler o conteúdo
        text = await run_in_threadpool(extractor.extract, data)  # fora do event loop
        return await self._parser.parse(text, filename)
