"""SessionService: liga roteiro, participante e sessão ao InterviewService (EV-01)."""

import pytest

from app.core.errors import ConflictError, NotFoundError
from app.db.seed import CORE_QUESTIONS
from app.schemas.participant import Participant
from app.schemas.script import DEFAULT_SCRIPT_ID, InterviewScript, Question
from app.services.interview_service import DEFAULT_CLOSING
from app.services.session_service import SessionService

pytestmark = pytest.mark.anyio


@pytest.fixture
def sessions_service(
    session_repository, script_repository, participant_repository, synthesis_repository, service
):
    return SessionService(
        sessions=session_repository,
        scripts=script_repository,
        participants=participant_repository,
        interview=service,
        syntheses=synthesis_repository,
    )


@pytest.fixture
async def custom_script(script_repository) -> InterviewScript:
    return await script_repository.create(
        InterviewScript(
            titulo="Transporte",
            perguntas=[Question(ordem=1, texto="Como você vem?"), Question(ordem=2, texto="E a volta?")],
        )
    )


async def _start(service: SessionService, script_id=None, participant_id=None):
    """Abre pelo caminho de produção (`open`) e devolve (estado gravado, primeira pergunta)."""
    opened = await service.open(script_id, participant_id)
    return await service.get(opened.session_id), opened.pergunta


class TestStart:
    async def test_without_script_uses_the_seed_from_the_database(self, sessions_service, session_repository):
        state, pergunta = await _start(sessions_service)

        assert pergunta == CORE_QUESTIONS[0]
        stored = await session_repository.get(state.session_id)
        assert stored.script_id == DEFAULT_SCRIPT_ID
        assert stored.conversation[0].pergunta_ordem == 1

    async def test_with_a_script_and_participant_links_both(
        self, sessions_service, session_repository, participant_repository, custom_script
    ):
        person = await participant_repository.create(Participant(apelido="Lia"))

        state, pergunta = await _start(sessions_service, custom_script.script_id, person.participant_id)

        assert pergunta == "Como você vem?"
        stored = await session_repository.get(state.session_id)
        assert (stored.script_id, stored.participant_id) == (custom_script.script_id, person.participant_id)

    async def test_unknown_script_is_not_found(self, sessions_service, session_repository):
        with pytest.raises(NotFoundError, match="Roteiro não encontrado."):
            await _start(sessions_service, "nao-existe")
        assert await session_repository.count() == 0

    async def test_unknown_participant_is_not_found(self, sessions_service, session_repository):
        with pytest.raises(NotFoundError, match="Participante não encontrado."):
            await _start(sessions_service, participant_id="fantasma")
        assert await session_repository.count() == 0

    async def test_inactive_script_is_a_conflict(self, sessions_service, script_repository, custom_script):
        custom_script.ativo = False
        await script_repository.save(custom_script)

        with pytest.raises(ConflictError, match="não está recebendo entrevistas"):
            await _start(sessions_service, custom_script.script_id)


class TestTurns:
    async def test_turn_uses_the_session_script_and_persists(
        self, sessions_service, session_repository, fake_llm, custom_script
    ):
        state, _ = await _start(sessions_service, custom_script.script_id)
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
        state, _ = await _start(sessions_service)
        await sessions_service.finish(state.session_id)

        with pytest.raises(ConflictError, match="já foi encerrada"):
            await sessions_service.take_turn(state.session_id, "oi")
        assert fake_llm.prompts == []

    async def test_deleted_script_keeps_the_answer_and_closes(
        self, sessions_service, script_repository, session_repository, fake_llm, custom_script
    ):
        state, _ = await _start(sessions_service, custom_script.script_id)
        await script_repository.delete(custom_script.script_id)

        session, fala = await sessions_service.take_turn(state.session_id, "vou de ônibus")

        assert fala == DEFAULT_CLOSING and session.finished
        stored = await session_repository.get(state.session_id)
        assert stored.finished and "vou de ônibus" in [t.text for t in stored.conversation]
        assert fake_llm.prompts == []


class TestConcurrency:
    async def test_finish_during_a_slow_turn_is_not_overwritten(
        self, sessions_service, session_repository, script_repository, service, fake_llm
    ):
        """/turn lê a sessão, o LLM demora, /finish encerra; o turno não pode reabrir a sessão."""
        state, _ = await _start(sessions_service)
        fake_llm.queue(action="deepen", next_utterance="Me conta mais?")
        stale = await session_repository.get(state.session_id)
        script = await script_repository.get_default()
        await service.run_turn(stale, script, "resposta lenta")  # turno ainda não gravado

        await sessions_service.finish(state.session_id)  # usuário clicou em Concluir

        with pytest.raises(ConflictError, match="alterada por outra ação"):
            await session_repository.save(stale)
        assert (await session_repository.get(state.session_id)).finished is True

    async def test_take_turn_loses_to_a_finish_that_happened_meanwhile(
        self, sessions_service, session_repository, fake_llm
    ):
        """Pelo caminho real: o LLM 'demora' e o /finish acontece durante a decisão."""
        state, _ = await _start(sessions_service)
        original = fake_llm.complete_json

        async def slow_decision(prompt):
            await sessions_service.finish(state.session_id)  # Concluir durante o PROCESSANDO
            return await original(prompt)

        fake_llm.complete_json = slow_decision
        fake_llm.queue(action="deepen", next_utterance="Me conta mais?")

        with pytest.raises(ConflictError, match="alterada por outra ação"):
            await sessions_service.take_turn(state.session_id, "resposta lenta")
        stored = await session_repository.get(state.session_id)
        assert stored.finished is True
        assert "Me conta mais?" not in [t.text for t in stored.conversation]

    async def test_finish_is_idempotent_without_new_writes(self, sessions_service, session_repository):
        state, _ = await _start(sessions_service)
        await sessions_service.finish(state.session_id)
        version = (await session_repository.get(state.session_id)).versao

        again = await sessions_service.finish(state.session_id)

        assert again.finished
        assert (await session_repository.get(state.session_id)).versao == version

    async def test_finish_retries_when_a_turn_saves_in_between(
        self, sessions_service, session_repository, monkeypatch
    ):
        state, _ = await _start(sessions_service)
        original_get = session_repository.get_or_raise
        calls = {"n": 0}

        async def get_then_turn_saves(session_id):
            loaded = await original_get(session_id)
            calls["n"] += 1
            if calls["n"] == 1:  # um /turn grava entre a leitura e a escrita do /finish
                concurrent = await original_get(session_id)
                await session_repository.save(concurrent)
            return loaded

        monkeypatch.setattr(session_repository, "get_or_raise", get_then_turn_saves)

        finished = await sessions_service.finish(state.session_id)

        assert finished.finished and calls["n"] == 2
        assert (await session_repository.get(state.session_id)).finished is True

    async def test_finish_gives_up_after_a_second_conflict(
        self, sessions_service, session_repository, monkeypatch
    ):
        state, _ = await _start(sessions_service)
        original_get = session_repository.get_or_raise

        async def always_concurrent(session_id):
            loaded = await original_get(session_id)
            await session_repository.save(await original_get(session_id))
            return loaded

        monkeypatch.setattr(session_repository, "get_or_raise", always_concurrent)

        with pytest.raises(ConflictError):
            await sessions_service.finish(state.session_id)

    async def test_session_deleted_mid_turn_is_not_found(
        self, sessions_service, session_repository, fake_llm, monkeypatch
    ):
        state, _ = await _start(sessions_service)
        fake_llm.queue(action="deepen", next_utterance="E aí?")

        original_save = session_repository.save

        async def delete_then_save(session):
            await session_repository.delete(session.session_id)
            return await original_save(session)

        monkeypatch.setattr(session_repository, "save", delete_then_save)
        with pytest.raises(NotFoundError, match="Sessão não encontrada."):
            await sessions_service.take_turn(state.session_id, "oi")


class TestFinishGetDetails:
    async def test_finish_persists_the_closing(self, sessions_service, session_repository):
        state, _ = await _start(sessions_service)

        finished = await sessions_service.finish(state.session_id)

        assert finished.finished
        assert (await session_repository.get(state.session_id)).status == "concluida"

    async def test_finish_unknown_session(self, sessions_service):
        with pytest.raises(NotFoundError):
            await sessions_service.finish("x")

    async def test_get(self, sessions_service):
        state, _ = await _start(sessions_service)

        assert (await sessions_service.get(state.session_id)).session_id == state.session_id
        with pytest.raises(NotFoundError):
            await sessions_service.get("x")

    async def test_details_joins_the_script(self, sessions_service):
        state, _ = await _start(sessions_service)

        details = await sessions_service.details(state.session_id)

        assert details.script.script_id == DEFAULT_SCRIPT_ID
        assert details.participant is None
        with pytest.raises(NotFoundError):
            await sessions_service.details("x")


class TestDelete:
    async def test_removes_the_session_and_its_synthesis(
        self, sessions_service, session_repository, synthesis_repository
    ):
        from app.schemas.synthesis import Synthesis

        state, _ = await _start(sessions_service)
        await synthesis_repository.save_for_session(
            Synthesis(escopo="sessao", session_id=state.session_id, script_id=state.script_id, resumo="r")
        )

        await sessions_service.delete(state.session_id)

        assert await session_repository.get(state.session_id) is None
        assert await synthesis_repository.get_for_session(state.session_id) is None

    async def test_unknown_session_is_not_found(self, sessions_service):
        with pytest.raises(NotFoundError, match="Sessão não encontrada."):
            await sessions_service.delete("nao-existe")
