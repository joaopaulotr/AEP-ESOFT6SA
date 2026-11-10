"""Extratores de texto por formato. Trabalham só em memória: nada vai para disco nem para log."""

import csv
import io
from abc import ABC, abstractmethod
from typing import ClassVar

from app.core.errors import ImportFileError, UnsupportedFileError

UNSUPPORTED_MESSAGE = "Formato não suportado. Envie .txt, .md, .csv, .docx ou .pdf."
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
        cells = [cell.strip() for row in csv.reader(io.StringIO(text), dialect) for cell in row]
        return "\n".join(cell for cell in cells if cell)


class DocxExtractor(TextExtractor):
    extensions = (".docx",)

    def extract(self, data: bytes) -> str:
        from docx import Document

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
            pages = [page.extract_text() or "" for page in reader.pages]
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
