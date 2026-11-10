"""Extratores de texto do upload de questionário (EV-30)."""

from io import BytesIO

import pytest
from docx import Document
from pypdf import PdfWriter

from app.core.errors import ImportFileError, UnsupportedFileError
from app.importing.extractors import (
    CsvExtractor,
    DocxExtractor,
    PdfExtractor,
    PlainTextExtractor,
    extractor_for,
)


def _docx_bytes() -> bytes:
    doc = Document()
    doc.add_paragraph("Como você vai ao trabalho?")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Quanto tempo leva?"
    table.rows[0].cells[1].text = ""
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _text_pdf(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 20 100 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref)
    return out


def test_plain_text_decodes_utf8_and_latin1():
    assert PlainTextExtractor().extract("Olá?".encode("utf-8")) == "Olá?"
    assert PlainTextExtractor().extract("Olá?".encode("latin-1")) == "Olá?"


def test_csv_joins_non_empty_cells_one_per_line():
    data = b"Pergunta 1;Pergunta 2\n,\nA?,B?\n"
    assert CsvExtractor().extract(data).splitlines() == ["Pergunta 1;Pergunta 2", "A?", "B?"]


def test_docx_reads_paragraphs_and_table_cells():
    text = DocxExtractor().extract(_docx_bytes())
    assert "Como você vai ao trabalho?" in text
    assert "Quanto tempo leva?" in text


def test_docx_corrupted_is_422():
    with pytest.raises(ImportFileError):
        DocxExtractor().extract(b"nao e docx")


def test_pdf_with_text():
    assert "Qual seu bairro?" in PdfExtractor().extract(_text_pdf("Qual seu bairro?"))


def test_pdf_without_text_is_422():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buffer = BytesIO()
    writer.write(buffer)
    with pytest.raises(ImportFileError, match="não tem texto"):
        PdfExtractor().extract(buffer.getvalue())


def test_pdf_corrupted_is_422():
    with pytest.raises(ImportFileError):
        PdfExtractor().extract(b"lixo")


@pytest.mark.parametrize(
    "name,cls",
    [
        ("a.txt", PlainTextExtractor),
        ("A.MD", PlainTextExtractor),
        ("a.csv", CsvExtractor),
        ("a.docx", DocxExtractor),
        ("a.b.pdf", PdfExtractor),
    ],
)
def test_extractor_for_known(name, cls):
    assert isinstance(extractor_for(name), cls)


@pytest.mark.parametrize("name", ["a.exe", "semextensao", "a.doc", ""])
def test_extractor_for_unknown_is_415(name):
    with pytest.raises(UnsupportedFileError, match="Formato não suportado"):
        extractor_for(name)


def test_csv_cell_over_field_limit_is_422():
    with pytest.raises(ImportFileError):
        CsvExtractor().extract(b"a," + b"x" * 200_000 + b"\n")


def test_docx_zip_bomb_is_422():
    import zipfile

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b"0" * (5 * 1024 * 1024))
    with pytest.raises(ImportFileError, match="grande demais"):
        DocxExtractor().extract(buffer.getvalue())


def test_pdf_stops_after_50_pages_or_enough_text(monkeypatch):
    from app.importing import extractors

    calls = []

    class Page:
        def extract_text(self):
            calls.append(1)
            return "linha?"

    class Reader:
        def __init__(self, _):
            self.pages = [Page() for _ in range(200)]

    monkeypatch.setattr("pypdf.PdfReader", Reader)
    PdfExtractor().extract(b"x")
    assert len(calls) == 50

    calls.clear()

    class BigPage(Page):
        def extract_text(self):
            calls.append(1)
            return "a" * 21_000

    class BigReader(Reader):
        def __init__(self, _):
            self.pages = [BigPage() for _ in range(10)]

    monkeypatch.setattr("pypdf.PdfReader", BigReader)
    PdfExtractor().extract(b"x")
    assert len(calls) == 1
