import pytest

from app.repositories.session_repository import SessionRepository
from app.schemas.interview import InterviewState, Turn
from app.services.synthesis_service import SynthesisService

pytestmark = pytest.mark.anyio


@pytest.fixture
def repository(fake_db) -> SessionRepository:
    return SessionRepository(database=fake_db)


@pytest.fixture
def synthesis(repository, fake_llm) -> SynthesisService:
    return SynthesisService(session_repository=repository, llm_client=fake_llm)


@pytest.fixture
def finished_state() -> InterviewState:
    return InterviewState(
        finished=True,
        profile={"cargo": "analista", "sentimento": "frustrado"},
        conversation=[
            Turn(role="interviewer", text="Como é seu dia a dia?"),
            Turn(role="participant", text="Passo o dia respondendo chamados."),
            Turn(role="interviewer", text="O que mais te frustra?"),
            Turn(role="participant", text="Repetir a mesma resposta dez vezes."),
        ],
    )


class TestConstruction:
    def test_uses_the_injected_collaborators(self, repository, fake_llm):
        synthesis = SynthesisService(session_repository=repository, llm_client=fake_llm)

        assert synthesis._sessions is repository
        assert synthesis._llm is fake_llm

    def test_builds_a_default_repository(self, fake_llm):
        synthesis = SynthesisService(llm_client=fake_llm)

        assert isinstance(synthesis._sessions, SessionRepository)

    def test_default_construction_never_reaches_the_network(self):
        with pytest.raises(AssertionError, match="cliente OpenAI real"):
            SynthesisService()


class TestGuards:
    async def test_raises_when_the_session_does_not_exist(self, synthesis):
        with pytest.raises(ValueError, match="Sessão não encontrada."):
            await synthesis.synthesize("inexistente")

    async def test_raises_when_the_interview_is_not_finished(self, synthesis, repository):
        state = InterviewState(finished=False)
        await repository.create(state)

        with pytest.raises(ValueError, match="antes de encerrar a entrevista"):
            await synthesis.synthesize(state.session_id)

    async def test_does_not_call_the_model_when_a_guard_trips(self, synthesis, fake_llm):
        with pytest.raises(ValueError):
            await synthesis.synthesize("inexistente")

        assert fake_llm.prompts == []


class TestSynthesize:
    async def test_returns_the_text_produced_by_the_model(
        self, synthesis, repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_payload("Relatório de síntese da entrevista.")

        result = await synthesis.synthesize(finished_state.session_id)

        assert result == "Relatório de síntese da entrevista."

    async def test_prompt_carries_the_full_conversation(
        self, synthesis, repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_payload("texto")

        await synthesis.synthesize(finished_state.session_id)

        prompt = fake_llm.last_prompt
        assert "interviewer: Como é seu dia a dia?" in prompt
        assert "participant: Passo o dia respondendo chamados." in prompt
        assert "participant: Repetir a mesma resposta dez vezes." in prompt

    async def test_prompt_carries_the_profile(
        self, synthesis, repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_payload("texto")

        await synthesis.synthesize(finished_state.session_id)

        assert "analista" in fake_llm.last_prompt
        assert "frustrado" in fake_llm.last_prompt

    async def test_prompt_keeps_the_report_instructions(
        self, synthesis, repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_payload("texto")

        await synthesis.synthesize(finished_state.session_id)

        prompt = fake_llm.last_prompt
        assert "Resumo geral" in prompt
        assert "Não invente informação" in prompt

    async def test_reads_the_session_through_the_repository(
        self, synthesis, repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_payload("texto")

        result = await synthesis.synthesize(finished_state.session_id)

        assert result == "texto"

    async def test_handles_an_interview_without_conversation(
        self, synthesis, repository, fake_llm
    ):
        state = InterviewState(finished=True)
        await repository.create(state)
        fake_llm.queue_payload("texto")

        await synthesis.synthesize(state.session_id)

        assert "(sem histórico ainda)" in fake_llm.last_prompt
