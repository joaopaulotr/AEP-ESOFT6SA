import pytest

from app.services.safety import check_safety, mentions_stop


@pytest.mark.parametrize(
    "text",
    [
        "quero parar",
        "pode parar por favor",
        "vamos parar aqui",
        "quero parar, muito obrigado",
        "por favor, quero parar",
        "chega de entrevista",
        "encerra a entrevista",
        "para a entrevista, por favor",
        "para a entrevista",
        "quero encerrar a entrevista",
        "não quero mais fazer a entrevista",
        "não quero continuar a entrevista",
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
        "eu quero morrer",
        "Quero me matar.",
        "vou me matar",
        "penso em suicídio",
        "quero me suicidar",
        "pensei em tirar minha própria vida",
    ],
)
def test_distress_terms(text):
    assert check_safety(text) == "sofrimento"


@pytest.mark.parametrize(
    "text",
    [
        # Expressões comuns que NÃO são sofrimento: ficam para o LLM (risco), sem atalho.
        "vou me matar de trabalhar esse mês",
        "eu quero me matar de rir com isso",
        "quero me matar de estudar pra prova",
        "quero acabar com tudo isso de papelada",
        "trabalho numa campanha de prevenção ao suicídio",
        "quase morri de rir",
        "quero morrer de vergonha quando atraso",
        "o suicídio é tema de palestra na escola",
    ],
)
def test_distress_false_positives_do_not_trigger(text):
    assert check_safety(text) == "nenhum"


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
        "Vim para a entrevista",
        "quando termina a entrevista?",
        "quanto tempo falta, quando encerra a entrevista?",
        "que horas vai parar a entrevista?",
        "chega mais",
        "Cheguei para a entrevista e o ônibus atrasou",
        "a gente chega lá",
        "não quero mais ônibus lotado",
        "não quero parar de usar o ônibus",
        "eu quero parar de pegar dois ônibus todo dia",
        "",
        # Respostas curtas a perguntas de sim/não: o LLM decide (B1).
        "Não quero mais.",
        "Não quero continuar.",
        "chega",
        "chega!",
        "não quero mais, obrigado",
        # Pergunta nunca encerra de forma determinística: o LLM decide.
        "quero saber quando vamos parar a entrevista?",
        "você pode me dizer quando vai encerrar a entrevista?",
        "quando a gente pode encerrar a entrevista?",
        "quero parar a entrevista?",
        "pode parar a entrevista?",
        "como faço pra parar a entrevista",
        "será que dá pra encerrar a entrevista",
    ],
)
def test_common_false_positives_do_not_trigger(text):
    assert check_safety(text) == "nenhum"


def test_distress_wins_over_stop_request():
    # Segurança primeiro: o acolhimento já encerra e indica o CVV.
    assert check_safety("quero parar, quero morrer") == "sofrimento"


@pytest.mark.parametrize(
    "text",
    [
        "Não quero mais.", "não quero continuar", "chega", "chega por hoje", "quero parar",
        "encerra a entrevista", "quero encerrar", "Não, não quero mais.", "Não quero mais responder",
        "não quero continuar não", "Já deu, chega", "Sério, chega.", "quero sair daqui",
        "para, por favor", "pode encerrar",
    ],
)
def test_mentions_stop_uses_the_broad_list(text):
    # Lista ampla: só usada quando o LLM falhou e não pode decidir.
    assert mentions_stop(text)


@pytest.mark.parametrize(
    "text",
    ["pego dois ônibus", "quando termina a entrevista?", "de ônibus, todo dia", "o trajeto é longo"],
)
def test_mentions_stop_ignores_regular_answers(text):
    assert not mentions_stop(text)
