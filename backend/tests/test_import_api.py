"""POST /scripts/upload e POST /scripts com origem (EV-30)."""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.api.deps import get_import_service
from app.importing.questionnaire_parser import QuestionnaireParser
from app.services.import_service import ImportService
from app.core.config import settings
from app.main import app

API = "/api/v1/scripts"


@pytest.fixture
def client(fake_llm):
    service = ImportService(QuestionnaireParser(fake_llm))
    app.dependency_overrides[get_import_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _up(client, name="q.txt", data=b"1. Qual seu bairro?"):
    return client.post(f"{API}/upload", files={"file": (name, data)})


def test_upload_ok_does_not_save(client, fake_llm):
    fake_llm.queue_payload(
        {"titulo": "T", "tema": "", "descricao": "", "perguntas": [{"texto": "Fale do bairro", "objetivo": "o"}]}
    )
    response = _up(client)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["origem"]["tipo"] == "upload" and body["origem"]["arquivo"] == "q.txt"
    assert body["perguntas"][0]["texto"] == "Fale do bairro"
    assert body["avisos"] == []
    assert all(s["titulo"] != "T" for s in client.get(API).json())


def test_upload_413(client, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 10)
    response = _up(client, data=b"x" * 11)
    assert response.status_code == 413
    assert response.json()["detail"] == "Arquivo maior que 2 MB."


def test_upload_415(client):
    response = _up(client, name="a.exe")
    assert response.status_code == 415
    assert "Formato não suportado" in response.json()["detail"]


def test_upload_422_no_questions(client, fake_llm):
    fake_llm.queue_payload({})
    response = _up(client, data=b"nada aqui")
    assert response.status_code == 422
    assert response.json()["detail"] == "Não encontrei perguntas no arquivo."


def test_upload_422_scanned_pdf(client):
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buffer = BytesIO()
    writer.write(buffer)
    response = _up(client, name="a.pdf", data=buffer.getvalue())
    assert response.status_code == 422
    assert "não tem texto" in response.json()["detail"]


def test_create_script_keeps_upload_origin(client):
    body = {
        "titulo": "Roteiro",
        "perguntas": [{"texto": "Fale do bairro"}],
        "origem": {"tipo": "upload", "arquivo": "q.docx", "extraido_em": "2026-11-09T10:00:00Z"},
    }
    created = client.post(API, json=body)
    assert created.status_code == 201, created.text
    got = client.get(f"{API}/{created.json()['script_id']}").json()
    assert got["origem"]["tipo"] == "upload" and got["origem"]["arquivo"] == "q.docx"


def test_create_script_without_origin_is_manual(client):
    created = client.post(API, json={"titulo": "R", "perguntas": [{"texto": "a?"}]})
    assert created.json()["origem"]["tipo"] == "manual"
