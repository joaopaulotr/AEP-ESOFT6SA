"""Extratores de texto por formato. Trabalham só em memória: nada vai para disco nem para log."""

import csv
import io
import zipfile
from abc import ABC, abstractmethod
from typing import ClassVar

from app.core.errors import ImportFileError, UnsupportedFileError

UNSUPPORTED_MESSAGE = "Formato não suportado. Envie .txt, .md, .csv, .docx ou .pdf."
DOCX_TOO_BIG_MESSAGE = "O arquivo .docx é grande demais para ler."
MAX_DOCX_UNCOMPRESSED = 20 * 1024 * 1024
MAX_DOCX_RATIO = 100
MAX_PDF_PAGES = 50
MAX_PDF_CHARS = 20_000
UNREADABLE_MESSAGE = "Não consegui abrir o arquivo. Confira se ele não está corrompido."


class TextExtractor(ABC):
    extensions: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    def extract(self, data: bytes) -> str: ...


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


class PlainTextExtractor(TextExtractor):
    extensions = (".txt", ".md")

    def extract(self, data: bytes) -> str:
        return _decode(data)


class CsvExtractor(TextExtractor):
    extensions = (".csv",)

    def extract(self, data: bytes) -> str:
        text = _decode(data)
        try:
            dialect = csv.Sniffer().sniff(text[:2048], delimiters=",\t")
        except csv.Error:
            dialect = csv.excel
        try:
            cells = [cell.strip() for row in csv.reader(io.StringIO(text), dialect) for cell in row]
        except csv.Error as exc:
            raise ImportFileError(UNREADABLE_MESSAGE) from exc
        return "\n".join(cell for cell in cells if cell)


def _check_zip_size(data: bytes) -> None:
    """Recusa arquivo-bomba (muito grande depois de descompactar) antes de abrir."""
    try:
        infos = zipfile.ZipFile(io.BytesIO(data)).infolist()
    except zipfile.BadZipFile as exc:
        raise ImportFileError(UNREADABLE_MESSAGE) from exc
    if sum(i.file_size for i in infos) > MAX_DOCX_UNCOMPRESSED or any(
        i.file_size > MAX_DOCX_RATIO * max(i.compress_size, 1) for i in infos
    ):
        raise ImportFileError(DOCX_TOO_BIG_MESSAGE)


class DocxExtractor(TextExtractor):
    extensions = (".docx",)

    def extract(self, data: bytes) -> str:
        from docx import Document

        _check_zip_size(data)
        try:
            document = Document(io.BytesIO(data))
        except Exception as exc:
            raise ImportFileError(UNREADABLE_MESSAGE) from exc
        lines = [p.text for p in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                lines.extend(cell.text for cell in row.cells)
        return "\n".join(line.strip() for line in lines if line.strip())


class PdfExtractor(TextExtractor):
    extensions = (".pdf",)

    def extract(self, data: bytes) -> str:
        from pypdf import PdfReader

        try:
            reader = PdfReader(io.BytesIO(data))
            pages: list[str] = []
            total = 0
            for page in reader.pages[:MAX_PDF_PAGES]:
                pages.append(page.extract_text() or "")
                total += len(pages[-1])
                if total >= MAX_PDF_CHARS:
                    break
        except Exception as exc:
            raise ImportFileError(UNREADABLE_MESSAGE) from exc
        text = "\n".join(pages).strip()
        if not text:
            raise ImportFileError("O PDF não tem texto (pode ser digitalizado).")
        return text


_EXTRACTORS: tuple[TextExtractor, ...] = (
    PlainTextExtractor(),
    CsvExtractor(),
    DocxExtractor(),
    PdfExtractor(),
)


def extractor_for(filename: str) -> TextExtractor:
    name = filename.lower()
    for extractor in _EXTRACTORS:
        if name.endswith(extractor.extensions):
            return extractor
    raise UnsupportedFileError(UNSUPPORTED_MESSAGE)
