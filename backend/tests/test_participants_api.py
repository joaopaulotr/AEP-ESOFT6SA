"""Rotas de participantes (EV-03)."""

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app
from app.schemas.interview import InterviewState

API = "/api/v1/participants"


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_create_with_no_identification_is_allowed(client):
    response = client.post(API, json={})

    assert response.status_code == 201
    body = response.json()
    assert body["apelido"] is None and body["canal"] == "voz"
    assert body["participant_id"] and "_id" not in body


def test_create_get_and_list(client):
    created = client.post(API, json={"apelido": "Maria", "regiao": "Sul", "canal": "texto"}).json()

    fetched = client.get(f"{API}/{created['participant_id']}").json()
    assert fetched["participant_id"] == created["participant_id"]
    assert (fetched["apelido"], fetched["regiao"], fetched["canal"]) == ("Maria", "Sul", "texto")
    assert [p["participant_id"] for p in client.get(API).json()] == [created["participant_id"]]


def test_create_rejects_invalid_channel(client):
    assert client.post(API, json={"canal": "telepatia"}).status_code == 422


def test_get_unknown_is_404(client):
    response = client.get(f"{API}/nao-existe")

    assert response.status_code == 404
    assert response.json() == {"detail": "Participante não encontrado."}


def test_put_changes_only_what_was_sent(client):
    created = client.post(API, json={"apelido": "Maria", "regiao": "Sul"}).json()

    body = client.put(f"{API}/{created['participant_id']}", json={"apelido": "Mari"}).json()

    assert body["apelido"] == "Mari" and body["regiao"] == "Sul"
    assert body["updated_at"] >= created["updated_at"]
    assert client.get(f"{API}/{created['participant_id']}").json()["apelido"] == "Mari"


def test_put_can_clear_a_field_with_null(client):
    created = client.post(API, json={"apelido": "Maria"}).json()

    body = client.put(f"{API}/{created['participant_id']}", json={"apelido": None}).json()

    assert body["apelido"] is None


def test_put_unknown_is_404(client):
    assert client.put(f"{API}/nao-existe", json={"apelido": "x"}).status_code == 404


def test_delete_without_sessions_removes_it(client):
    created = client.post(API, json={}).json()

    assert client.delete(f"{API}/{created['participant_id']}").status_code == 204
    assert client.get(f"{API}/{created['participant_id']}").status_code == 404


def test_delete_with_sessions_is_409_and_keeps_history(client):
    created = client.post(API, json={"apelido": "Maria"}).json()
    state = InterviewState(participant_id=created["participant_id"])
    client.portal.call(deps.get_session_repository().create, state)

    response = client.delete(f"{API}/{created['participant_id']}")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Este participante tem entrevistas registradas e não pode ser apagado."
    }
    assert client.get(f"{API}/{created['participant_id']}").status_code == 200


def test_delete_unknown_is_404(client):
    assert client.delete(f"{API}/nao-existe").status_code == 404
