"""Parser de questionário e serviço de importação (EV-30)."""

import pytest

from app.core.config import settings
from app.core.errors import EmptyQuestionnaireError, FileTooLargeError
from app.importing.questionnaire_parser import QuestionnaireParser, heuristic_parse
from app.providers.base import ProviderError
from app.services.import_service import ImportService

pytestmark = pytest.mark.anyio

FALLBACK = "A IA não conseguiu ler o arquivo; usei a leitura automática. Revise as perguntas."


def _payload(n: int = 2) -> dict:
    return {
        "titulo": "Mobilidade",
        "tema": "Transporte",
        "descricao": "Como as pessoas se locomovem",
        "perguntas": [{"texto": f"Conte sobre o trajeto {i}", "objetivo": "rotina"} for i in range(n)],
    }


async def test_parse_with_valid_llm(fake_llm):
    fake_llm.queue_payload(_payload())
    draft = await QuestionnaireParser(fake_llm).parse("1. Você usa ônibus?", "q.txt")
    assert draft.titulo == "Mobilidade"
    assert draft.perguntas[0].texto == "Conte sobre o trajeto 0"
    assert draft.origem.tipo == "upload" and draft.origem.arquivo == "q.txt"
    assert draft.origem.extraido_em is not None
    assert draft.avisos == []
    assert "1. Você usa ônibus?" in fake_llm.last_prompt


async def test_parse_invalid_json_falls_back(fake_llm):
    fake_llm.queue_payload({"foo": "bar"})
    draft = await QuestionnaireParser(fake_llm).parse(
        "1. Você usa ônibus?\n2) E metrô?", "meu-roteiro.txt"
    )
    assert [p.texto for p in draft.perguntas] == ["Você usa ônibus?", "E metrô?"]
    assert draft.titulo == "meu-roteiro"
    assert FALLBACK in draft.avisos


async def test_parse_provider_error_falls_back(fake_llm):
    fake_llm.queue_error(ProviderError("x"))
    draft = await QuestionnaireParser(fake_llm).parse("Qual seu bairro?", "q.md")
    assert len(draft.perguntas) == 1 and FALLBACK in draft.avisos


async def test_llm_zero_questions_falls_back(fake_llm):
    fake_llm.queue_payload(_payload(0))
    draft = await QuestionnaireParser(fake_llm).parse("Qual seu bairro?", "q.txt")
    assert FALLBACK in draft.avisos


async def test_no_questions_anywhere_is_422(fake_llm):
    fake_llm.queue_error(ProviderError("x"))
    with pytest.raises(EmptyQuestionnaireError, match="Não encontrei perguntas"):
        await QuestionnaireParser(fake_llm).parse("texto solto sem nada", "q.txt")


async def test_caps_at_20_with_warning(fake_llm):
    fake_llm.queue_payload(_payload(25))
    draft = await QuestionnaireParser(fake_llm).parse("x?", "q.txt")
    assert len(draft.perguntas) == 20
    assert "Mantive só as 20 primeiras perguntas." in draft.avisos


async def test_truncates_long_text(fake_llm):
    fake_llm.queue_payload(_payload())
    draft = await QuestionnaireParser(fake_llm).parse("a" * 30000 + "ZZQ", "q.txt")
    assert "ZZQ" not in fake_llm.last_prompt
    assert "O arquivo é grande; usei só o começo." in draft.avisos


def test_heuristic_bullets_numbering_dedupe():
    text = "Intro\n- Você usa ônibus?\n• Você usa ônibus?\n3) Quanto paga?\n4. Descreva seu dia\nOutra coisa?"
    draft = heuristic_parse(text, "x.txt")
    assert [p.texto for p in draft.perguntas] == [
        "Você usa ônibus?",
        "Quanto paga?",
        "Outra coisa?",
    ]


def test_heuristic_numbered_without_question_mark_needs_an_interrogative_word():
    text = "1. Introdução\n2. Qual é o seu bairro\n3) Como você chega ao trabalho\n4. Dados pessoais"
    draft = heuristic_parse(text, "x.txt")
    assert [p.texto for p in draft.perguntas] == ["Qual é o seu bairro", "Como você chega ao trabalho"]


async def test_unexpected_llm_exception_falls_back_and_logs_only_the_type(fake_llm, caplog):
    fake_llm.queue_error(KeyError("segredo"))
    with caplog.at_level("WARNING"):
        draft = await QuestionnaireParser(fake_llm).parse("Qual seu bairro?", "q.txt")
    assert [p.texto for p in draft.perguntas] == ["Qual seu bairro?"]
    assert FALLBACK in draft.avisos
    assert "KeyError" in caplog.text and "segredo" not in caplog.text


def test_megabytes_are_formatted_in_portuguese():
    from app.services.import_service import format_megabytes

    assert format_megabytes(2 * 1024 * 1024) == "2 MB"
    assert format_megabytes(512 * 1024) == "0,5 MB"


def test_heuristic_caps_20():
    draft = heuristic_parse("\n".join(f"{i}. P{i}?" for i in range(1, 30)), "x.txt")
    assert len(draft.perguntas) == 20
    assert "Mantive só as 20 primeiras perguntas." in draft.avisos


async def test_service_builds_draft_and_checks_size(fake_llm):
    fake_llm.queue_payload(_payload())
    service = ImportService(QuestionnaireParser(fake_llm))
    draft = await service.build_draft("q.txt", b"Qual seu bairro?")
    assert draft.perguntas
    with pytest.raises(FileTooLargeError, match="Arquivo maior que 2 MB."):
        await service.build_draft("q.txt", b"x" * (settings.max_upload_bytes + 1))


async def test_empty_text_is_422_without_llm_call(fake_llm):
    with pytest.raises(EmptyQuestionnaireError):
        await QuestionnaireParser(fake_llm).parse("  \n ", "q.txt")
    assert fake_llm.prompts == []
