from datetime import datetime, timedelta, timezone

import pytest

from app.core.errors import ConflictError, CorruptDocumentError, NotFoundError
from app.repositories.session_repository import SessionRepository
from app.schemas.interview import InterviewState, Turn
from app.schemas.participant import Participant

pytestmark = pytest.mark.anyio


@pytest.fixture
def repository(session_repository) -> SessionRepository:
    return session_repository


def interviewer(acao, ordem, text="?") -> Turn:
    return Turn(role="interviewer", text=text, acao=acao, pergunta_ordem=ordem)


def participant(ordem, text="resposta") -> Turn:
    return Turn(role="participant", text=text, pergunta_ordem=ordem)


class TestConstruction:
    def test_uses_the_interview_sessions_collection(self, fake_db):
        assert SessionRepository(fake_db)._collection.name == "interview_sessions"

    def test_declares_the_relationship_indexes(self, repository):
        names = {index.document["name"] for index in repository.indexes()}

        assert names == {"session_id_unico", "script_id_data", "script_id_atualizada", "participant_id"}


class TestCrud:
    async def test_round_trip_keeps_conversation_profile_and_references(self, repository):
        state = InterviewState(
            script_id="transporte",
            participant_id="p1",
            profile={"cargo": "designer"},
            conversation=[interviewer(None, 1, "Como é seu dia?"), participant(1, "Corrido.")],
        )
        await repository.create(state)

        found = await repository.get(state.session_id)

        assert found.script_id == "transporte" and found.participant_id == "p1"
        assert found.profile == {"cargo": "designer"}
        assert [(t.role, t.text, t.pergunta_ordem) for t in found.conversation] == [
            ("interviewer", "Como é seu dia?", 1),
            ("participant", "Corrido.", 1),
        ]

    async def test_document_has_status_and_nested_metrics(self, repository, sessions):
        state = InterviewState(finished=True)
        await repository.create(state)

        raw = await sessions.find_one({"session_id": state.session_id})

        assert raw["status"] == "concluida"
        assert raw["metricas"] == {
            "llm_input_tokens": 0,
            "llm_output_tokens": 0,
            "stt_seconds": 0.0,
            "tts_chars": 0,
            "tokens": 0,
            "segundos_audio": 0.0,
            "custo_usd": 0.0,
        }

    async def test_save_refreshes_updated_at_and_status(self, repository, sessions, monkeypatch):
        state = InterviewState()
        await repository.create(state)
        later = state.updated_at + timedelta(seconds=5)

        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return later

        monkeypatch.setattr("app.repositories.base.datetime", FixedDatetime)
        state.finished = True
        await repository.save(state)

        raw = await sessions.find_one({"session_id": state.session_id})
        assert state.updated_at == later
        assert raw["status"] == "concluida"

    async def test_saving_an_unknown_session_writes_nothing(self, repository, sessions):
        assert await repository.save(InterviewState()) is False
        assert await sessions.count_documents({}) == 0

    async def test_get_or_raise_message(self, repository):
        with pytest.raises(NotFoundError, match="Sessão não encontrada."):
            await repository.get_or_raise("x")

    async def test_unique_session_id(self, repository):
        await repository.ensure_indexes()
        state = InterviewState()
        await repository.create(state)

        with pytest.raises(ConflictError):
            await repository.create(state)

    async def test_loads_a_document_written_by_v010(self, repository, sessions):
        await sessions.insert_one(
            {
                "session_id": "antiga",
                "asked_indices": [],
                "current_index": 0,
                "conversation": [{"role": "interviewer", "text": "Oi", "timestamp": datetime.now(timezone.utc)}],
                "profile": {},
                "finished": True,
                "synthesis": "texto antigo",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        )

        found = await repository.get("antiga")

        assert found.script_id == "entrevista-generalista"
        assert found.status == "concluida"


class TestListings:
    async def test_list_by_script_and_by_participant(self, repository):
        a = InterviewState(script_id="s1", participant_id="p1")
        b = InterviewState(script_id="s1")
        c = InterviewState(script_id="s2", participant_id="p1")
        for state in (a, b, c):
            await repository.create(state)

        assert {s.session_id for s in await repository.list_by_script("s1")} == {a.session_id, b.session_id}
        assert {s.session_id for s in await repository.list_by_participant("p1")} == {a.session_id, c.session_id}
        assert await repository.list_by_script("nenhum") == []


class TestGetDetails:
    async def test_joins_script_and_participant(
        self, repository, script_repository, participant_repository, script
    ):
        await script_repository.create(script)
        person = await participant_repository.create(Participant(apelido="Zé", regiao="Norte"))
        state = await repository.create(
            InterviewState(script_id=script.script_id, participant_id=person.participant_id)
        )

        details = await repository.get_details(state.session_id)

        assert details.session.session_id == state.session_id
        assert details.script.titulo == "Entrevista generalista"
        assert len(details.script.perguntas) == 4
        assert details.participant.apelido == "Zé"

    async def test_anonymous_session_has_no_participant(
        self, repository, script_repository, participant_repository, script
    ):
        await script_repository.create(script)
        await participant_repository.create(Participant(apelido="outra pessoa"))
        state = await repository.create(InterviewState(script_id=script.script_id))

        details = await repository.get_details(state.session_id)

        assert details.participant is None
        assert details.script is not None

    async def test_dangling_script_reference_is_reported_as_none(self, repository):
        state = await repository.create(InterviewState(script_id="apagado"))

        details = await repository.get_details(state.session_id)

        assert details.script is None

    async def test_unknown_session_returns_none(self, repository):
        assert await repository.get_details("x") is None


class TestScriptStats:
    async def test_empty_script_has_zeroed_stats(self, repository):
        stats = await repository.script_stats("vazio")

        assert stats.total_sessoes == 0 and stats.taxa_conclusao == 0.0
        assert stats.acoes == [] and stats.aprofundamentos_por_pergunta == []

    async def test_aggregates_sessions_actions_and_deepenings(self, repository):
        # Sessão 1 (concluída): pergunta 1 com 2 aprofundamentos, pergunta 2 com 0.
        one = InterviewState(
            script_id="s",
            finished=True,
            conversation=[
                interviewer(None, 1), participant(1),
                interviewer("deepen", 1), participant(1),
                interviewer("deepen", 1), participant(1),
                interviewer("advance", 2), participant(2),
                interviewer("finish", 2),
            ],
        )
        # Sessão 2 (em andamento): pergunta 1 sem aprofundamento.
        two = InterviewState(
            script_id="s",
            conversation=[interviewer(None, 1), participant(1), interviewer("advance", 2)],
        )
        other = InterviewState(script_id="outro", finished=True, conversation=[interviewer("deepen", 1)])
        for state in (one, two, other):
            await repository.create(state)

        stats = await repository.script_stats("s")

        assert stats.total_sessoes == 2
        assert stats.concluidas == 1
        assert stats.taxa_conclusao == 0.5
        assert stats.media_respostas == 2.5  # (4 + 1) / 2
        assert [(a.acao, a.total) for a in stats.acoes] == [("advance", 2), ("deepen", 2), ("finish", 1)]
        assert [(q.pergunta_ordem, q.media_aprofundamentos) for q in stats.aprofundamentos_por_pergunta] == [
            (1, 1.0),  # (2 + 0) / 2 sessões
            (2, 0.0),
        ]


def v010_document(session_id: str, finished: bool, synthesis=None) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "session_id": session_id,
        "asked_indices": [0],
        "current_index": 1,
        "conversation": [
            {"role": "interviewer", "text": "Para começar...", "timestamp": now},
            {"role": "participant", "text": "Trabalho à noite.", "timestamp": now},
        ],
        "profile": {"turno": "noite"},
        "finished": finished,
        "synthesis": synthesis,
        "created_at": now,
        "updated_at": now,
    }


class TestBackfillLegacy:
    async def test_completes_v010_sessions_in_the_database(self, repository, sessions):
        await sessions.insert_one(v010_document("antiga", finished=True))
        received = []

        async def on_synthesis(session_id, text):
            received.append((session_id, text))

        migrated = await repository.backfill_legacy(on_synthesis)

        raw = await sessions.find_one({"session_id": "antiga"})
        assert migrated == 1
        assert raw["script_id"] == "entrevista-generalista"
        assert raw["status"] == "concluida" and raw["versao"] == 0
        assert raw["participant_id"] is None and "synthesis" not in raw
        assert received == []  # synthesis era None

    async def test_migrated_legacy_session_matches_the_status_filter_of_summaries(
        self, repository, sessions
    ):
        await sessions.insert_one(v010_document("velha-ok", finished=True))
        await sessions.insert_one(v010_document("velha-aberta", finished=False))

        async def ignore(session_id, text):
            pass

        await repository.backfill_legacy(ignore)

        done = await repository.list_summaries("entrevista-generalista", status="concluida")
        open_ = await repository.list_summaries("entrevista-generalista", status="em_andamento")
        assert [s.session_id for s in done] == ["velha-ok"]
        assert [s.session_id for s in open_] == ["velha-aberta"]

    async def test_hands_the_old_synthesis_over_before_removing_it(self, repository, sessions):
        await sessions.insert_one(v010_document("antiga", finished=True, synthesis="Relatório antigo."))
        received = []

        async def on_synthesis(session_id, text):
            received.append((session_id, text))

        await repository.backfill_legacy(on_synthesis)

        assert received == [("antiga", "Relatório antigo.")]

    async def test_is_idempotent_and_skips_current_sessions(self, repository, sessions):
        await repository.create(InterviewState())
        await sessions.insert_one(v010_document("antiga", finished=False))

        async def ignore(session_id, text):
            raise AssertionError("não deveria ser chamado")

        assert await repository.backfill_legacy(ignore) == 1
        assert await repository.backfill_legacy(ignore) == 0

    async def test_migrated_sessions_join_lookup_and_stats(self, repository, sessions, script_repository):
        await script_repository.ensure_seed()
        await sessions.insert_one(v010_document("antiga", finished=True))

        async def ignore(session_id, text):
            pass

        await repository.backfill_legacy(ignore)

        assert (await repository.get_details("antiga")).script.titulo == "Entrevista generalista"
        stats = await repository.script_stats("entrevista-generalista")
        assert (stats.total_sessoes, stats.concluidas) == (1, 1)
        assert [s.session_id for s in await repository.list_by_script("entrevista-generalista")] == ["antiga"]


    async def test_document_outside_the_model_does_not_stop_the_migration(self, repository, sessions):
        """A v0.1.0 podia gravar perfil não-string (RK-07): migra mesmo assim."""
        broken = v010_document("quebrada", finished=True, synthesis="Relatório.")
        broken["profile"] = {"idade": 42, "turnos": ["manhã"]}
        await sessions.insert_one(broken)
        received = []

        async def on_synthesis(session_id, text):
            received.append(session_id)

        assert await repository.backfill_legacy(on_synthesis) == 1
        raw = await sessions.find_one({"session_id": "quebrada"})
        assert raw["script_id"] == "entrevista-generalista" and raw["status"] == "concluida"
        assert received == ["quebrada"]

    async def test_failure_while_saving_the_synthesis_keeps_the_legacy_document(self, repository, sessions):
        await sessions.insert_one(v010_document("antiga", finished=True, synthesis="Relatório antigo."))

        async def failing(session_id, text):
            raise RuntimeError("queda no meio da migração")

        with pytest.raises(RuntimeError):
            await repository.backfill_legacy(failing)
        raw = await sessions.find_one({"session_id": "antiga"})
        assert "script_id" not in raw and raw["synthesis"] == "Relatório antigo."

        received = []

        async def ok(session_id, text):
            received.append(text)

        assert await repository.backfill_legacy(ok) == 1  # a próxima execução termina o trabalho
        assert received == ["Relatório antigo."]


class TestCorruptRelatedDocuments:
    async def test_corrupt_participant_in_details_hides_its_content(
        self, repository, participant_repository, fake_db
    ):
        await fake_db["participants"].insert_one({"participant_id": "p", "canal": "Maria, Recife"})
        state = await repository.create(InterviewState(participant_id="p"))

        with pytest.raises(CorruptDocumentError) as error:
            await repository.get_details(state.session_id)
        assert "participants" in str(error.value) and "canal" in str(error.value)
        assert "Maria" not in str(error.value)
        assert error.value.__cause__ is None and error.value.__suppress_context__


class TestCountByScript:
    async def test_counts_only_the_requested_scripts(self, repository):
        await repository.create(InterviewState(script_id="a", finished=True))
        await repository.create(InterviewState(script_id="a"))
        await repository.create(InterviewState(script_id="b"))

        assert await repository.count_by_script(["a"]) == {"a": (2, 1)}
        assert await repository.count_by_script([]) == {}


class TestBackfillMissingDates:
    async def test_legacy_session_without_dates_is_listed_after_backfill(self, repository, sessions):
        document = v010_document("sem-data", finished=True)
        del document["created_at"], document["updated_at"]
        await sessions.insert_one(document)

        async def ignore(session_id, text):
            pass

        await repository.backfill_legacy(ignore)

        found = await repository.list_summaries("entrevista-generalista")
        assert [s.session_id for s in found] == ["sem-data"]
        assert found[0].created_at is not None and found[0].updated_at is not None
