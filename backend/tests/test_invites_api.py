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

    def test_slug_is_normalized_on_lookup(self, client):
        script = _roteiro(client)

        response = client.get(f"{API}/convite/{script['slug_convite'].upper()}")

        assert response.status_code == 200
        assert response.json()["slug"] == script["slug_convite"]

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


class TestStartRace:
    def test_deactivated_between_lookup_and_open_removes_participant(self, client, monkeypatch):
        from app.core.errors import ConflictError
        from app.services.session_service import SessionService

        script = _roteiro(client)
        participants = deps.get_participant_repository()
        antes = client.portal.call(participants.count)

        async def _conflito(self, *args, **kwargs):
            raise ConflictError("Este roteiro não está recebendo entrevistas.")

        monkeypatch.setattr(SessionService, "open", _conflito)
        response = client.post(f"{API}/convite/{script['slug_convite']}/sessao", json={})

        assert response.status_code == 404
        assert response.json()["detail"] == "Convite inválido ou encerrado."
        assert client.portal.call(participants.count) == antes

    @pytest.mark.parametrize("erro", ["not_found", "runtime"])
    def test_any_failure_opening_the_session_removes_participant(self, client, monkeypatch, erro):
        from app.core.errors import NotFoundError
        from app.services.session_service import SessionService

        script = _roteiro(client)
        participants = deps.get_participant_repository()
        antes = client.portal.call(participants.count)

        async def _falha(self, *args, **kwargs):
            if erro == "not_found":
                raise NotFoundError("Roteiro não encontrado.")
            raise RuntimeError("banco caiu")

        monkeypatch.setattr(SessionService, "open", _falha)
        if erro == "not_found":
            response = client.post(f"{API}/convite/{script['slug_convite']}/sessao", json={})
            assert response.status_code == 404
            assert response.json()["detail"] == "Convite inválido ou encerrado."
        else:
            with pytest.raises(RuntimeError):
                client.post(f"{API}/convite/{script['slug_convite']}/sessao", json={})
        assert client.portal.call(participants.count) == antes


def _iniciar(client, script: dict, canal: str = "voz") -> str:
    response = client.post(f"{API}/convite/{script['slug_convite']}/sessao", json={"canal": canal})
    assert response.status_code == 201, response.text
    return response.json()["session_id"]


class TestPublicSession:
    def test_returns_only_the_minimum_state(self, client):
        script = _roteiro(client)
        sid = _iniciar(client, script)

        response = client.get(f"{API}/convite/{script['slug_convite']}/sessao/{sid}")

        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "session_id", "titulo", "perguntas_total", "current_index", "finished",
            "acolhimento", "persona", "conversation",
        }
        assert (body["session_id"], body["titulo"], body["perguntas_total"]) == (sid, "Transporte público", 2)
        assert (body["current_index"], body["finished"], body["acolhimento"]) == (0, False, False)
        assert body["persona"] == {"nome": script["persona"]["nome"], "tom": script["persona"]["tom"]}
        assert [set(t) for t in body["conversation"]] == [{"role", "text"}]
        assert body["conversation"][0]["text"].endswith("Como você se desloca?")

    def test_reports_the_welcome_after_distress(self, client):
        script = _roteiro(client)
        sid = _iniciar(client, script)
        client.post(f"{API}/turn/{sid}", json={"texto": "quero morrer"})

        body = client.get(f"{API}/convite/{script['slug_convite']}/sessao/{sid}").json()

        assert body["finished"] is True and body["acolhimento"] is True
        assert "alerta" not in str(body)

    def test_session_of_another_script_is_404(self, client):
        mine, other = _roteiro(client), _roteiro(client)
        sid = _iniciar(client, other)

        response = client.get(f"{API}/convite/{mine['slug_convite']}/sessao/{sid}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Convite inválido ou encerrado."

    @pytest.mark.parametrize("slug_ok", [True, False])
    def test_unknown_session_or_slug_is_404(self, client, slug_ok):
        script = _roteiro(client)
        sid = _iniciar(client, script)
        url = (
            f"{API}/convite/{script['slug_convite']}/sessao/nao-existe"
            if slug_ok
            else f"{API}/convite/nao-existe/sessao/{sid}"
        )
        response = client.get(url)
        assert response.status_code == 404
        assert response.json()["detail"] == "Convite inválido ou encerrado."

    def test_still_readable_after_the_script_is_deactivated(self, client):
        script = _roteiro(client)
        sid = _iniciar(client, script)
        client.put(f"{API}/scripts/{script['script_id']}", json={"ativo": False})

        response = client.get(f"{API}/convite/{script['slug_convite']}/sessao/{sid}")

        assert response.status_code == 200


class TestPublicChannel:
    def test_switch_updates_the_participant_channel(self, client):
        script = _roteiro(client)
        sid = _iniciar(client, script, canal="voz")

        response = client.post(
            f"{API}/convite/{script['slug_convite']}/sessao/{sid}/canal", json={"canal": "texto"}
        )

        assert response.status_code == 204
        assert _participante_da_sessao(client, sid).canal == "texto"
        again = client.post(
            f"{API}/convite/{script['slug_convite']}/sessao/{sid}/canal", json={"canal": "texto"}
        )
        assert again.status_code == 204

    def test_invalid_channel_is_422(self, client):
        script = _roteiro(client)
        sid = _iniciar(client, script)
        response = client.post(
            f"{API}/convite/{script['slug_convite']}/sessao/{sid}/canal", json={"canal": "fax"}
        )
        assert response.status_code == 422

    def test_session_of_another_script_is_404(self, client):
        mine, other = _roteiro(client), _roteiro(client)
        sid = _iniciar(client, other)
        response = client.post(
            f"{API}/convite/{mine['slug_convite']}/sessao/{sid}/canal", json={"canal": "texto"}
        )
        assert response.status_code == 404
        assert _participante_da_sessao(client, sid).canal == "voz"

    def test_session_without_participant_is_a_no_op(self, client):
        script = _roteiro(client)
        sid = client.post(f"{API}/session", json={"script_id": script["script_id"]}).json()["session_id"]
        response = client.post(
            f"{API}/convite/{script['slug_convite']}/sessao/{sid}/canal", json={"canal": "texto"}
        )
        assert response.status_code == 204
