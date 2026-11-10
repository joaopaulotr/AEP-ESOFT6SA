"""Convite público (EV-31/EV-34): entrada por link sem login e QR Code."""

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.core.config import settings
from app.main import app

API = "/api/v1"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(deps.settings, "llm_provider", "fake")  # nunca a OpenAI real
    with TestClient(app) as test_client:
        yield test_client


def _roteiro(client) -> dict:
    response = client.post(
        f"{API}/scripts",
        json={
            "titulo": "Transporte público",
            "tema": "Mobilidade",
            "perguntas": [{"texto": "Como você se desloca?"}, {"texto": "O que atrapalha?"}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _link(slug: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/e/{slug}"


def _participante_da_sessao(client, session_id: str):
    session = client.portal.call(deps.get_session_repository().get_or_raise, session_id)
    return client.portal.call(
        deps.get_participant_repository().get_or_raise, session.participant_id
    )


class TestPublicInvite:
    def test_active_script_exposes_only_public_fields(self, client):
        script = _roteiro(client)
        slug = script["slug_convite"]

        response = client.get(f"{API}/convite/{slug}")

        assert response.status_code == 200
        assert response.json() == {
            "slug": slug,
            "titulo": "Transporte público",
            "tema": "Mobilidade",
            "descricao": script["descricao"],
            "persona": script["persona"],
            "perguntas_total": 2,
            "link": _link(slug),
        }

    def test_unknown_slug_is_404(self, client):
        response = client.get(f"{API}/convite/nao-existe")

        assert response.status_code == 404
        assert response.json()["detail"] == "Convite inválido ou encerrado."

    def test_inactive_script_is_404(self, client):
        script = _roteiro(client)
        client.put(f"{API}/scripts/{script['script_id']}", json={"ativo": False})

        response = client.get(f"{API}/convite/{script['slug_convite']}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Convite inválido ou encerrado."


class TestStartSession:
    def test_creates_participant_with_channel_and_linked_session(self, client):
        script = _roteiro(client)

        response = client.post(
            f"{API}/convite/{script['slug_convite']}/sessao",
            json={"canal": "texto", "apelido": "  Ze ", "regiao": ""},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["script_id"] == script["script_id"]
        assert body["titulo"] == "Transporte público"
        assert body["perguntas_total"] == 2
        participant = _participante_da_sessao(client, body["session_id"])
        assert (participant.canal, participant.apelido, participant.regiao) == ("texto", "Ze", None)

    def test_body_is_optional_and_defaults_to_voice(self, client):
        script = _roteiro(client)

        response = client.post(f"{API}/convite/{script['slug_convite']}/sessao")

        assert response.status_code == 201
        assert _participante_da_sessao(client, response.json()["session_id"]).canal == "voz"

    @pytest.mark.parametrize(
        "campo,tamanho", [("apelido", 41), ("faixa_etaria", 21), ("regiao", 61)]
    )
    def test_too_long_fields_are_422(self, client, campo, tamanho):
        script = _roteiro(client)

        response = client.post(
            f"{API}/convite/{script['slug_convite']}/sessao", json={campo: "x" * tamanho}
        )

        assert response.status_code == 422

    def test_invalid_channel_is_422(self, client):
        script = _roteiro(client)

        response = client.post(
            f"{API}/convite/{script['slug_convite']}/sessao", json={"canal": "fax"}
        )

        assert response.status_code == 422

    def test_unknown_or_inactive_slug_is_404(self, client):
        assert client.post(f"{API}/convite/nao-existe/sessao", json={}).status_code == 404

        script = _roteiro(client)
        client.put(f"{API}/scripts/{script['script_id']}", json={"ativo": False})
        response = client.post(f"{API}/convite/{script['slug_convite']}/sessao", json={})

        assert response.status_code == 404
        assert response.json()["detail"] == "Convite inválido ou encerrado."


class TestOrganizerLinkAndQr:
    def test_script_invite_link(self, client):
        script = _roteiro(client)

        response = client.get(f"{API}/scripts/{script['script_id']}/convite")

        assert response.status_code == 200
        assert response.json() == {
            "slug": script["slug_convite"],
            "link": _link(script["slug_convite"]),
        }

    def test_summary_has_link_convite(self, client):
        script = _roteiro(client)

        resumo = next(
            s for s in client.get(f"{API}/scripts").json() if s["script_id"] == script["script_id"]
        )

        assert resumo["link_convite"] == _link(script["slug_convite"])

    def test_qrcode_is_svg(self, client):
        script = _roteiro(client)

        response = client.get(f"{API}/scripts/{script['script_id']}/qrcode.svg")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/svg+xml")
        assert "<svg" in response.text

    def test_unknown_script_is_404_for_link_and_qr(self, client):
        assert client.get(f"{API}/scripts/nada/convite").status_code == 404
        assert client.get(f"{API}/scripts/nada/qrcode.svg").status_code == 404
