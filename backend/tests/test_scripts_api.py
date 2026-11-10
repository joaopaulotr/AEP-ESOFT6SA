"""Rotas de roteiros (EV-03): CRUD, resumo com contagens e as regras de 409."""

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app
from app.schemas.interview import InterviewState

API = "/api/v1/scripts"
DEFAULT_ID = "entrevista-generalista"


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _novo(client, **extra) -> dict:
    body = {
        "titulo": "Transporte público",
        "tema": "Mobilidade",
        "perguntas": [
            {"texto": "Como você se desloca?", "objetivo": "rotina"},
            {"texto": "O que mais atrapalha?", "max_aprofundamentos": 3},
        ],
        **extra,
    }
    response = client.post(API, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def _gravar_sessao(client, script_id: str, *, finished: bool = False) -> str:
    state = InterviewState(script_id=script_id, finished=finished)
    client.portal.call(deps.get_session_repository().create, state)
    return state.session_id


class TestCreate:
    def test_assigns_order_by_position_and_defaults(self, client):
        script = _novo(client)

        assert [(q["ordem"], q["texto"]) for q in script["perguntas"]] == [
            (1, "Como você se desloca?"),
            (2, "O que mais atrapalha?"),
        ]
        assert script["perguntas"][0]["max_aprofundamentos"] == 2
        assert script["perguntas"][1]["max_aprofundamentos"] == 3
        assert script["ativo"] is True
        assert script["persona"] == {"nome": "Ana", "tom": "acolhedor"}
        assert script["slug_convite"].startswith("transporte-publico-")
        assert "_id" not in script

    def test_accepts_a_persona(self, client):
        script = _novo(client, persona={"nome": "Bia", "tom": "formal"})

        assert script["persona"] == {"nome": "Bia", "tom": "formal"}

    @pytest.mark.parametrize(
        "body",
        [
            {"titulo": "", "perguntas": [{"texto": "a?"}]},
            {"titulo": "   ", "perguntas": [{"texto": "a?"}]},
            {"titulo": "x", "perguntas": []},
            {"titulo": "x", "perguntas": [{"texto": "   "}]},
            {"titulo": "x", "perguntas": [{"texto": "a?", "max_aprofundamentos": 9}]},
            {"perguntas": [{"texto": "a?"}]},
        ],
    )
    def test_invalid_body_is_422(self, client, body):
        assert client.post(API, json=body).status_code == 422


class TestRead:
    def test_get_returns_the_script(self, client):
        created = _novo(client)

        fetched = client.get(f"{API}/{created['script_id']}").json()

        # o Mongo guarda datas em milissegundos: o resto tem de ser idêntico
        assert {k: v for k, v in fetched.items() if not k.endswith("_at")} == {
            k: v for k, v in created.items() if not k.endswith("_at")
        }

    def test_get_unknown_is_404_in_portuguese(self, client):
        response = client.get(f"{API}/nao-existe")

        assert response.status_code == 404
        assert response.json() == {"detail": "Roteiro não encontrado."}

    def test_list_summarizes_with_counts_newest_first_and_includes_the_default(self, client):
        created = _novo(client)
        script_id = created["script_id"]
        _gravar_sessao(client, script_id, finished=True)
        _gravar_sessao(client, script_id, finished=True)
        _gravar_sessao(client, script_id)

        body = client.get(API).json()

        assert [item["script_id"] for item in body] == [script_id, DEFAULT_ID]
        resumo = body[0]
        assert set(resumo) == {
            "script_id", "titulo", "tema", "descricao", "slug_convite", "ativo",
            "perguntas_total", "persona", "sessoes_total", "concluidas", "em_andamento",
        }
        assert resumo["perguntas_total"] == 2
        assert (resumo["sessoes_total"], resumo["concluidas"], resumo["em_andamento"]) == (3, 2, 1)
        assert resumo["persona"] == {"nome": "Ana", "tom": "acolhedor"}
        assert (body[1]["sessoes_total"], body[1]["perguntas_total"]) == (0, 4)

    def test_ativos_false_lists_inactive_too(self, client):
        created = _novo(client)
        client.put(f"{API}/{created['script_id']}", json={"ativo": False})

        ativos = [s["script_id"] for s in client.get(API).json()]
        todos = [s["script_id"] for s in client.get(API, params={"ativos": "false"}).json()]

        assert created["script_id"] not in ativos
        assert created["script_id"] in todos


class TestUpdate:
    def test_partial_update_keeps_the_rest(self, client):
        created = _novo(client)

        response = client.put(f"{API}/{created['script_id']}", json={"titulo": "Novo título"})

        assert response.status_code == 200
        body = response.json()
        assert body["titulo"] == "Novo título"
        assert body["perguntas"] == created["perguntas"]
        assert body["tema"] == "Mobilidade"
        assert body["slug_convite"] == created["slug_convite"]

    def test_replaces_questions_renumbering_by_position(self, client):
        created = _novo(client)

        body = client.put(
            f"{API}/{created['script_id']}",
            json={"perguntas": [{"texto": "Só uma?"}, {"texto": "E outra?"}, {"texto": "E mais?"}]},
        ).json()

        assert [q["ordem"] for q in body["perguntas"]] == [1, 2, 3]

    def test_changing_questions_with_any_session_is_409(self, client):
        for finished in (False, True):
            created = _novo(client)
            _gravar_sessao(client, created["script_id"], finished=finished)

            response = client.put(
                f"{API}/{created['script_id']}", json={"perguntas": [{"texto": "Outra?"}]}
            )

            assert response.status_code == 409
            assert response.json() == {
                "detail": "Este roteiro já tem entrevistas. Crie um novo roteiro para mudar as perguntas."
            }
            assert client.get(f"{API}/{created['script_id']}").json()["perguntas"] == created["perguntas"]

    def test_other_fields_can_change_during_an_interview(self, client):
        created = _novo(client)
        _gravar_sessao(client, created["script_id"])

        response = client.put(f"{API}/{created['script_id']}", json={"ativo": False, "tema": "Novo"})

        assert response.status_code == 200
        assert response.json()["ativo"] is False

    def test_questions_can_change_when_the_script_has_no_sessions(self, client):
        created = _novo(client)

        response = client.put(f"{API}/{created['script_id']}", json={"perguntas": [{"texto": "Nova?"}]})

        assert response.status_code == 200
        assert [q["texto"] for q in response.json()["perguntas"]] == ["Nova?"]

    def test_default_script_cannot_be_deactivated_nor_have_questions_changed(self, client):
        detail = "O roteiro padrão não pode ser desativado nem ter as perguntas alteradas."
        before = client.get(f"{API}/{DEFAULT_ID}").json()

        for body in ({"ativo": False}, {"perguntas": [{"texto": "Outra?"}]}):
            response = client.put(f"{API}/{DEFAULT_ID}", json=body)
            assert response.status_code == 409
            assert response.json() == {"detail": detail}

        after = client.get(f"{API}/{DEFAULT_ID}").json()
        assert after["ativo"] is True and after["perguntas"] == before["perguntas"]

    def test_default_script_still_accepts_other_edits(self, client):
        response = client.put(
            f"{API}/{DEFAULT_ID}",
            json={"titulo": "Padrão", "tema": "t", "descricao": "d", "persona": {"nome": "Bia", "tom": "neutro"}, "ativo": True},
        )

        assert response.status_code == 200
        assert response.json()["titulo"] == "Padrão"
        assert response.json()["persona"] == {"nome": "Bia", "tom": "neutro"}

    def test_unknown_is_404(self, client):
        assert client.put(f"{API}/nao-existe", json={"titulo": "x"}).status_code == 404

    @pytest.mark.parametrize("body", [{"titulo": ""}, {"perguntas": []}, {"perguntas": [{"texto": ""}]}])
    def test_invalid_body_is_422(self, client, body):
        created = _novo(client)

        assert client.put(f"{API}/{created['script_id']}", json=body).status_code == 422


class TestDelete:
    def test_without_sessions_removes_it(self, client):
        created = _novo(client)

        assert client.delete(f"{API}/{created['script_id']}").status_code == 204
        assert client.get(f"{API}/{created['script_id']}").status_code == 404

    def test_with_sessions_deactivates_instead(self, client):
        created = _novo(client)
        _gravar_sessao(client, created["script_id"], finished=True)

        assert client.delete(f"{API}/{created['script_id']}").status_code == 204

        kept = client.get(f"{API}/{created['script_id']}").json()
        assert kept["ativo"] is False

    def test_the_default_script_cannot_be_deleted(self, client):
        response = client.delete(f"{API}/{DEFAULT_ID}")

        assert response.status_code == 409
        assert response.json() == {"detail": "O roteiro padrão não pode ser apagado."}
        assert client.get(f"{API}/{DEFAULT_ID}").status_code == 200

    def test_unknown_is_404(self, client):
        assert client.delete(f"{API}/nao-existe").status_code == 404
