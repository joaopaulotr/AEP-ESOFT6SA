"""SessionService: liga roteiro, participante e sessão ao InterviewService (EV-01)."""

import pytest

from app.core.errors import ConflictError, NotFoundError
from app.db.seed import CORE_QUESTIONS
from app.schemas.participant import Participant
from app.schemas.script import DEFAULT_SCRIPT_ID, InterviewScript, Question
from app.services.session_service import SessionService

pytestmark = pytest.mark.anyio


@pytest.fixture
def sessions_service(session_repository, script_repository, participant_repository, service):
    return SessionService(
        sessions=session_repository,
        scripts=script_repository,
        participants=participant_repository,
        interview=service,
    )


@pytest.fixture
async def custom_script(script_repository) -> InterviewScript:
    return await script_repository.create(
        InterviewScript(
            titulo="Transporte",
            perguntas=[Question(ordem=1, texto="Como você vem?"), Question(ordem=2, texto="E a volta?")],
        )
    )


class TestStart:
    async def test_without_script_uses_the_seed_from_the_database(self, sessions_service, session_repository):
        state, pergunta = await sessions_service.start()

        assert pergunta == CORE_QUESTIONS[0]
        stored = await session_repository.get(state.session_id)
        assert stored.script_id == DEFAULT_SCRIPT_ID
        assert stored.conversation[0].pergunta_ordem == 1

    async def test_with_a_script_and_participant_links_both(
        self, sessions_service, session_repository, participant_repository, custom_script
    ):
        person = await participant_repository.create(Participant(apelido="Lia"))

        state, pergunta = await sessions_service.start(custom_script.script_id, person.participant_id)

        assert pergunta == "Como você vem?"
        stored = await session_repository.get(state.session_id)
        assert (stored.script_id, stored.participant_id) == (custom_script.script_id, person.participant_id)

    async def test_unknown_script_is_not_found(self, sessions_service, session_repository):
        with pytest.raises(NotFoundError, match="Roteiro não encontrado."):
            await sessions_service.start("nao-existe")
        assert await session_repository.count() == 0

    async def test_unknown_participant_is_not_found(self, sessions_service, session_repository):
        with pytest.raises(NotFoundError, match="Participante não encontrado."):
            await sessions_service.start(participant_id="fantasma")
        assert await session_repository.count() == 0

    async def test_inactive_script_is_a_conflict(self, sessions_service, script_repository, custom_script):
        custom_script.ativo = False
        await script_repository.save(custom_script)

        with pytest.raises(ConflictError, match="não está recebendo entrevistas"):
            await sessions_service.start(custom_script.script_id)


class TestTurns:
    async def test_turn_uses_the_session_script_and_persists(
        self, sessions_service, session_repository, fake_llm, custom_script
    ):
        state, _ = await sessions_service.start(custom_script.script_id)
        fake_llm.queue(action="advance", next_utterance="")

        _, fala = await sessions_service.take_turn(state.session_id, "de bicicleta")

        assert fala == "E a volta?"
        stored = await session_repository.get(state.session_id)
        assert stored.current_index == 1
        assert [t.text for t in stored.conversation][-2:] == ["de bicicleta", "E a volta?"]

    async def test_unknown_session(self, sessions_service):
        with pytest.raises(NotFoundError, match="Sessão não encontrada."):
            await sessions_service.take_turn("x", "oi")

    async def test_finished_session_is_a_conflict(self, sessions_service, fake_llm):
        state, _ = await sessions_service.start()
        await sessions_service.finish(state.session_id)

        with pytest.raises(ConflictError, match="já foi encerrada"):
            await sessions_service.take_turn(state.session_id, "oi")
        assert fake_llm.prompts == []

    async def test_deleted_script_is_reported(self, sessions_service, script_repository, custom_script):
        state, _ = await sessions_service.start(custom_script.script_id)
        await script_repository.delete(custom_script.script_id)

        with pytest.raises(NotFoundError, match="roteiro desta entrevista não existe mais"):
            await sessions_service.take_turn(state.session_id, "oi")


class TestFinishGetDetails:
    async def test_finish_persists_the_closing(self, sessions_service, session_repository):
        state, _ = await sessions_service.start()

        finished = await sessions_service.finish(state.session_id)

        assert finished.finished
        assert (await session_repository.get(state.session_id)).status == "concluida"

    async def test_finish_unknown_session(self, sessions_service):
        with pytest.raises(NotFoundError):
            await sessions_service.finish("x")

    async def test_get(self, sessions_service):
        state, _ = await sessions_service.start()

        assert (await sessions_service.get(state.session_id)).session_id == state.session_id
        with pytest.raises(NotFoundError):
            await sessions_service.get("x")

    async def test_details_joins_the_script(self, sessions_service):
        state, _ = await sessions_service.start()

        details = await sessions_service.details(state.session_id)

        assert details.script.script_id == DEFAULT_SCRIPT_ID
        assert details.participant is None
        with pytest.raises(NotFoundError):
            await sessions_service.details("x")
