"""Síntese de sessão estruturada com citações literais conferidas (EV-33)."""

import pytest

from app.providers.base import ProviderError
from app.schemas.interview import InterviewState, Turn
from app.services.citation_check import filter_literal_citations
from app.services.synthesis_service import SynthesisService

pytestmark = pytest.mark.anyio


@pytest.fixture
def synthesis(session_repository, synthesis_repository, fake_llm) -> SynthesisService:
    return SynthesisService(session_repository, synthesis_repository, fake_llm)


@pytest.fixture
def finished_state() -> InterviewState:
    return InterviewState(
        script_id="transporte",
        finished=True,
        conversation=[
            Turn(role="interviewer", text="Como vem para o trabalho?"),
            Turn(role="participant", text="Pego dois  ônibus\ne demoro   quase duas horas."),
            Turn(role="interviewer", text="E a volta?"),
            Turn(role="participant", text="A volta é pior, o ônibus lota."),
        ],
    )


def payload(**overrides) -> dict:
    base = {
        "resumo": "Participante perde muito tempo no transporte.",
        "temas": [
            {
                "tema": "Tempo de deslocamento",
                "pontos": ["Duas horas por trajeto"],
                "citacoes": ["demoro quase duas horas", "A volta é pior"],
            }
        ],
        "lacunas": ["Custo mensal não explorado"],
    }
    base.update(overrides)
    return base


class TestFilterLiteralCitations:
    def test_keeps_literal_after_whitespace_and_case_normalization(self):
        result = filter_literal_citations(
            ["DEMORO quase  duas horas"], ["Pego dois ônibus e demoro quase duas horas."]
        )

        assert result == ["DEMORO quase  duas horas"]

    def test_drops_invented_text(self):
        assert filter_literal_citations(["Eu odeio o metrô"], ["Pego dois ônibus."]) == []

    def test_strips_surrounding_quotes_before_checking(self):
        assert filter_literal_citations(['"dois ônibus"', "“dois ônibus”"], ["Pego dois ônibus."]) == [
            "dois ônibus",
            "dois ônibus",
        ]

    def test_drops_empty_and_quote_only(self):
        assert filter_literal_citations(["", "   ", '""'], ["algo"]) == []

    def test_must_come_from_a_single_turn(self):
        assert filter_literal_citations(["ônibus lota"], ["Pego dois ônibus.", "lota demais"]) == []


class TestStructuredSynthesis:
    async def test_saves_structure_with_literal_citations_only(
        self, synthesis, session_repository, synthesis_repository, fake_llm, finished_state
    ):
        await session_repository.create(finished_state)
        data = payload()
        data["temas"][0]["citacoes"].append("Eu nunca uso ônibus")  # inventada
        fake_llm.queue_payload(data)

        resumo = await synthesis.synthesize(finished_state.session_id)

        saved = await synthesis_repository.get_for_session(finished_state.session_id)
        assert resumo == data["resumo"] == saved.resumo
        assert saved.lacunas == ["Custo mensal não explorado"]
        theme = saved.temas[0]
        assert theme.tema == "Tempo de deslocamento" and theme.pontos == ["Duas horas por trajeto"]
        assert [(c.texto, c.session_id) for c in theme.citacoes] == [
            ("demoro quase duas horas", finished_state.session_id),
            ("A volta é pior", finished_state.session_id),
        ]

    async def test_interviewer_text_is_not_a_valid_citation(
        self, synthesis, session_repository, synthesis_repository, fake_llm, finished_state
    ):
        await session_repository.create(finished_state)
        fake_llm.queue_payload(
            payload(temas=[{"tema": "t", "pontos": [], "citacoes": ["Como vem para o trabalho?"]}])
        )

        await synthesis.synthesize(finished_state.session_id)

        saved = await synthesis_repository.get_for_session(finished_state.session_id)
        assert saved.temas[0].citacoes == []

    async def test_invalid_json_retries_once(
        self, synthesis, session_repository, synthesis_repository, fake_llm, finished_state
    ):
        await session_repository.create(finished_state)
        fake_llm.queue_payload({"resumo": 3}).queue_payload(payload())

        await synthesis.synthesize(finished_state.session_id)

        assert len(fake_llm.prompts) == 2
        saved = await synthesis_repository.get_for_session(finished_state.session_id)
        assert saved.temas

    async def test_still_invalid_falls_back_to_text_summary_only(
        self, synthesis, session_repository, synthesis_repository, fake_llm, finished_state
    ):
        await session_repository.create(finished_state)
        fake_llm.queue_payload("lixo").queue_payload({"x": 1}).queue_payload("Resumo em texto livre.")

        resumo = await synthesis.synthesize(finished_state.session_id)

        assert resumo == "Resumo em texto livre." and len(fake_llm.prompts) == 3
        saved = await synthesis_repository.get_for_session(finished_state.session_id)
        assert saved.resumo == resumo and saved.temas == [] and saved.lacunas == []

    async def test_provider_error_is_not_retried(
        self, synthesis, session_repository, fake_llm, finished_state
    ):
        await session_repository.create(finished_state)
        fake_llm.queue_error(ProviderError("fora"))

        with pytest.raises(ProviderError):
            await synthesis.synthesize(finished_state.session_id)

        assert len(fake_llm.prompts) == 1

    async def test_prompt_asks_for_json_and_literal_quotes(
        self, synthesis, session_repository, fake_llm, finished_state
    ):
        await session_repository.create(finished_state)
        fake_llm.queue_payload(payload())

        await synthesis.synthesize(finished_state.session_id)

        prompt = fake_llm.prompts[0]
        assert "JSON" in prompt and "literal" in prompt and "citacoes" in prompt
        assert "Pego dois  ônibus" in prompt

    async def test_blank_theme_names_are_dropped(
        self, synthesis, session_repository, synthesis_repository, fake_llm, finished_state
    ):
        await session_repository.create(finished_state)
        fake_llm.queue_payload(payload(temas=[{"tema": "  ", "pontos": ["x"], "citacoes": []}]))

        await synthesis.synthesize(finished_state.session_id)

        assert (await synthesis_repository.get_for_session(finished_state.session_id)).temas == []
