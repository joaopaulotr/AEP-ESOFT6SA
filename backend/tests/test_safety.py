import pytest

from app.services.safety import check_safety


@pytest.mark.parametrize(
    "text",
    [
        "quero parar",
        "Não quero mais",
        "NAO QUERO CONTINUAR",
        "pode parar por favor",
        "vamos parar aqui",
        "chega!",
        "chega",
        "não quero mais, obrigado",
        "para a entrevista",
        "quero encerrar a entrevista",
        "pode parar a entrevista, por favor eu tenho que sair agora e não dá mais",
    ],
)
def test_stop_requests(text):
    assert check_safety(text) == "pedido_parar"


@pytest.mark.parametrize(
    "text",
    [
        "às vezes penso em me matar",
        "quero tirar minha vida",
        "tenho vontade de me machucar",
        "não aguento mais viver assim",
        "eu quero morrer",
        "queria acabar com tudo",
        "tive pensamentos suicidas",
    ],
)
def test_distress_terms(text):
    assert check_safety(text) == "sofrimento"


@pytest.mark.parametrize(
    "text",
    [
        "o motorista vai parar o ônibus no ponto",
        "estou tentando parar de fumar",
        "o ônibus chegou e já chegamos tarde",
        "a chegada atrasa",
        "o ônibus mata o tempo da gente",
        "gosto de continuar a conversa",
        "o ônibus chega às 7h",
        "a gente chega lá",
        "não quero mais ônibus lotado",
        "não quero parar de usar o ônibus",
        "eu quero parar de pegar dois ônibus todo dia",
        "",
    ],
)
def test_common_false_positives_do_not_trigger(text):
    assert check_safety(text) == "nenhum"


def test_distress_wins_over_stop_request():
    # Segurança primeiro: o acolhimento já inclui a opção de encerrar.
    assert check_safety("quero parar, não aguento mais viver") == "sofrimento"
