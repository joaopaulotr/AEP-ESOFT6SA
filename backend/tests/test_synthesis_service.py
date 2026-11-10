import pytest

from app.core.errors import NotFoundError
from app.providers.base import ProviderError
from app.repositories.session_repository import SessionRepository
from app.schemas.interview import InterviewState, Turn
from app.services.synthesis_service import SynthesisService

pytestmark = pytest.mark.anyio


@pytest.fixture
def repository(session_repository) -> SessionRepository:
    return session_repository


@pytest.fixture
def synthesis(repository, synthesis_repository, fake_llm, script_repository) -> SynthesisService:
    return SynthesisService(
        session_repository=repository,
        synthesis_repository=synthesis_repository,
        llm=fake_llm,
        script_repository=script_repository,
    )


@pytest.fixture
def finished_state() -> InterviewState:
    return InterviewState(
        script_id="transporte",
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
    def test_uses_the_injected_collaborators(
        self, repository, synthesis_repository, fake_llm, script_repository
    ):
        synthesis = SynthesisService(repository, synthesis_repository, fake_llm, script_repository)

        assert synthesis._sessions is repository
        assert synthesis._syntheses is synthesis_repository
        assert synthesis._llm is fake_llm


class TestGuards:
    async def test_raises_when_the_session_does_not_exist(self, synthesis):
        with pytest.raises(NotFoundError, match="Sessão não encontrada."):
            await synthesis.synthesize("inexistente")

    async def test_raises_when_the_interview_is_not_finished(self, synthesis, repository):
        state = InterviewState(finished=False)
        await repository.create(state)

        with pytest.raises(ValueError, match="antes de encerrar a entrevista"):
            await synthesis.synthesize(state.session_id)

    async def test_does_not_call_the_model_when_a_guard_trips(self, synthesis, fake_llm):
        with pytest.raises(NotFoundError):
            await synthesis.synthesize("inexistente")

        assert fake_llm.prompts == []


class TestSynthesize:
    async def test_returns_the_text_produced_by_the_model(
        self, synthesis, repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_payload({"resumo": "Relatório de síntese da entrevista."})

        result = await synthesis.synthesize(finished_state.session_id)

        assert result == "Relatório de síntese da entrevista."

    async def test_prompt_carries_the_full_conversation(
        self, synthesis, repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_payload({"resumo": "texto"})

        await synthesis.synthesize(finished_state.session_id)

        prompt = fake_llm.last_prompt
        assert "interviewer: Como é seu dia a dia?" in prompt
        assert "participant: Passo o dia respondendo chamados." in prompt
        assert "participant: Repetir a mesma resposta dez vezes." in prompt

    async def test_prompt_carries_the_profile(
        self, synthesis, repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_payload({"resumo": "texto"})

        await synthesis.synthesize(finished_state.session_id)

        assert "analista" in fake_llm.last_prompt
        assert "frustrado" in fake_llm.last_prompt

    async def test_prompt_keeps_the_report_instructions(
        self, synthesis, repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_payload({"resumo": "texto"})

        await synthesis.synthesize(finished_state.session_id)

        prompt = fake_llm.last_prompt
        assert "citacoes" in prompt
        assert "Não invente informação" in prompt

    async def test_reads_the_session_through_the_repository(
        self, synthesis, repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_payload({"resumo": "texto"})

        result = await synthesis.synthesize(finished_state.session_id)

        assert result == "texto"

    async def test_refuses_an_interview_without_participant_answers(
        self, synthesis, repository, synthesis_repository, fake_llm
    ):
        state = InterviewState(
            finished=True, conversation=[Turn(role="interviewer", text="Como é seu dia a dia?")]
        )
        await repository.create(state)

        with pytest.raises(ValueError, match="A entrevista não tem respostas para resumir."):
            await synthesis.synthesize(state.session_id)

        assert fake_llm.prompts == []
        assert await synthesis_repository.count() == 0

    async def test_refuses_a_finished_interview_with_no_conversation(self, synthesis, repository):
        state = InterviewState(finished=True)
        await repository.create(state)

        with pytest.raises(ValueError, match="não tem respostas"):
            await synthesis.synthesize(state.session_id)


class TestProviderFailure:
    async def test_provider_error_propagates(self, synthesis, repository, fake_llm, finished_state):
        await repository.create(finished_state)
        fake_llm.queue_error(ProviderError("fora do ar"))

        with pytest.raises(ProviderError):
            await synthesis.synthesize(finished_state.session_id)


class TestStorage:
    async def test_saves_the_report_in_the_syntheses_collection(
        self, synthesis, repository, synthesis_repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_payload({"resumo": "Relatório."})

        await synthesis.synthesize(finished_state.session_id)

        stored = await synthesis_repository.get_for_session(finished_state.session_id)
        assert stored.escopo == "sessao"
        assert stored.script_id == "transporte"
        assert stored.resumo == "Relatório."
        assert stored.modelo == "FakeLLM"

    async def test_regenerating_replaces_the_previous_report(
        self, synthesis, repository, synthesis_repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_payload({"resumo": "v1"}).queue_payload({"resumo": "v2"})

        await synthesis.synthesize(finished_state.session_id)
        await synthesis.synthesize(finished_state.session_id, refresh=True)

        found = await synthesis_repository.list_for_script("transporte")
        assert [s.resumo for s in found] == ["v2"]

    async def test_session_document_does_not_carry_the_report(
        self, synthesis, repository, sessions, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_payload({"resumo": "Relatório."})

        await synthesis.synthesize(finished_state.session_id)

        raw = await sessions.find_one({"session_id": finished_state.session_id})
        assert "synthesis" not in raw

    async def test_provider_failure_stores_nothing(
        self, synthesis, repository, synthesis_repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_error(ProviderError("fora do ar"))

        with pytest.raises(ProviderError):
            await synthesis.synthesize(finished_state.session_id)
        assert await synthesis_repository.count() == 0


class TestSavedSynthesisIsReused:
    async def test_second_request_returns_the_saved_report_without_calling_the_model(
        self, synthesis, repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_payload({"resumo": "v1"})
        await synthesis.synthesize(finished_state.session_id)
        calls = len(fake_llm.prompts)

        result = await synthesis.synthesize(finished_state.session_id)

        assert result == "v1"
        assert len(fake_llm.prompts) == calls

    async def test_refresh_calls_the_model_again(
        self, synthesis, repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        fake_llm.queue_payload({"resumo": "v1"}).queue_payload({"resumo": "v2"})
        await synthesis.synthesize(finished_state.session_id)

        result = await synthesis.synthesize(finished_state.session_id, refresh=True)

        assert result == "v2"
        assert len(fake_llm.prompts) == 2


class TestGet:
    async def test_returns_the_saved_synthesis(self, synthesis, repository, fake_llm, finished_state):
        await repository.create(finished_state)
        fake_llm.queue_payload({"resumo": "v1"})
        await synthesis.synthesize(finished_state.session_id)

        saved = await synthesis.get(finished_state.session_id)

        assert saved.resumo == "v1" and saved.session_id == finished_state.session_id

    async def test_not_generated_yet_is_not_found(self, synthesis, repository, finished_state):
        await repository.create(finished_state)

        with pytest.raises(NotFoundError, match="Síntese ainda não gerada."):
            await synthesis.get(finished_state.session_id)

    async def test_unknown_session_is_not_found(self, synthesis):
        with pytest.raises(NotFoundError, match="Sessão não encontrada."):
            await synthesis.get("nao-existe")


class TestSessionDeletedWhileGenerating:
    async def test_orphan_synthesis_is_removed_and_the_request_is_404(
        self, synthesis, repository, synthesis_repository, fake_llm, finished_state
    ):
        await repository.create(finished_state)
        original = fake_llm.complete_json

        async def slow_text(prompt):
            await repository.delete(finished_state.session_id)  # apagada durante a geração
            return await original(prompt)

        fake_llm.complete_json = slow_text
        fake_llm.queue_payload({"resumo": "texto"})

        with pytest.raises(NotFoundError, match="Sessão não encontrada."):
            await synthesis.synthesize(finished_state.session_id)

        assert await synthesis_repository.get_for_session(finished_state.session_id) is None
        assert await synthesis_repository.count() == 0
