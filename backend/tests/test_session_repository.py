from datetime import datetime, timedelta, timezone

import pytest

from app.repositories.session_repository import SessionRepository
from app.schemas.interview import InterviewState, Turn

pytestmark = pytest.mark.anyio


@pytest.fixture
def repository(fake_db) -> SessionRepository:
    return SessionRepository(database=fake_db)


class TestConstruction:
    def test_uses_the_injected_database(self, fake_db):
        assert SessionRepository(database=fake_db)._db is fake_db

    def test_defaults_to_the_interview_sessions_collection(self, fake_db):
        assert SessionRepository(database=fake_db)._collection == "interview_sessions"

    def test_honours_a_custom_collection_name(self, fake_db):
        repository = SessionRepository(database=fake_db, collection="outra")

        assert repository._sessions is fake_db["outra"]

    def test_falls_back_to_the_default_database(self):
        from app.db import mongodb

        assert SessionRepository()._db is mongodb.db


class TestCreate:
    async def test_persists_the_serialized_state(self, repository, sessions):
        state = InterviewState(profile={"cargo": "analista"})

        await repository.create(state)

        assert len(sessions.documents) == 1
        assert sessions.documents[0]["session_id"] == state.session_id
        assert sessions.documents[0]["profile"] == {"cargo": "analista"}

    async def test_returns_the_same_state_object(self, repository):
        state = InterviewState()

        assert await repository.create(state) is state


class TestGet:
    async def test_returns_none_when_the_session_does_not_exist(self, repository):
        assert await repository.get("inexistente") is None

    async def test_rebuilds_the_state_from_the_document(self, repository):
        original = InterviewState(current_index=2, profile={"cargo": "designer"})
        await repository.create(original)

        found = await repository.get(original.session_id)

        assert found is not None
        assert found.session_id == original.session_id
        assert found.current_index == 2
        assert found.profile == {"cargo": "designer"}

    async def test_drops_the_mongo_object_id(self, repository, sessions):
        state = InterviewState()
        sessions.seed(state.model_dump())

        found = await repository.get(state.session_id)

        assert found is not None
        assert not hasattr(found, "_id")

    async def test_preserves_the_conversation(self, repository):
        state = InterviewState(
            conversation=[
                Turn(role="interviewer", text="Como é seu dia?"),
                Turn(role="participant", text="Corrido."),
            ]
        )
        await repository.create(state)

        found = await repository.get(state.session_id)

        assert [(turn.role, turn.text) for turn in found.conversation] == [
            ("interviewer", "Como é seu dia?"),
            ("participant", "Corrido."),
        ]

    async def test_ignores_sessions_with_another_id(self, repository):
        await repository.create(InterviewState())

        assert await repository.get("outro-id") is None


class TestSave:
    async def test_writes_the_updated_fields(self, repository, sessions):
        state = InterviewState()
        await repository.create(state)
        state.current_index = 3
        state.finished = True

        await repository.save(state)

        stored = await repository.get(state.session_id)
        assert stored.current_index == 3
        assert stored.finished is True

    async def test_refreshes_the_updated_at_timestamp(self, repository, monkeypatch):
        state = InterviewState()
        await repository.create(state)
        before = state.updated_at
        after = before + timedelta(seconds=1)

        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return after

        monkeypatch.setattr(
            "app.repositories.session_repository.datetime", FixedDatetime
        )
        await repository.save(state)

        assert state.updated_at == after
        assert state.updated_at > before
        assert state.updated_at.tzinfo is timezone.utc

    async def test_filters_by_the_session_id(self, repository, sessions):
        state = InterviewState()
        await repository.create(state)

        await repository.save(state)

        query, update = sessions.updates[-1]
        assert query == {"session_id": state.session_id}
        assert "$set" in update

    async def test_saving_an_unknown_session_writes_nothing(self, repository, sessions):
        await repository.save(InterviewState())

        assert sessions.documents == []


class TestDelete:
    async def test_removes_the_session(self, repository, sessions):
        state = InterviewState()
        await repository.create(state)

        await repository.delete(state.session_id)

        assert sessions.documents == []

    async def test_raises_when_the_session_does_not_exist(self, repository):
        with pytest.raises(ValueError, match="Sessão não encontrada."):
            await repository.delete("inexistente")

    async def test_keeps_the_other_sessions(self, repository, sessions):
        kept = InterviewState()
        removed = InterviewState()
        await repository.create(kept)
        await repository.create(removed)

        await repository.delete(removed.session_id)

        assert [document["session_id"] for document in sessions.documents] == [kept.session_id]


class TestListAll:
    async def test_returns_an_empty_list_when_there_is_nothing(self, repository):
        assert await repository.list_all() == []

    async def test_returns_every_session(self, repository):
        first = InterviewState(current_index=1)
        second = InterviewState(current_index=2)
        await repository.create(first)
        await repository.create(second)

        found = await repository.list_all()

        assert [state.session_id for state in found] == [first.session_id, second.session_id]
        assert [state.current_index for state in found] == [1, 2]

    async def test_drops_the_object_id_from_every_document(self, repository, sessions):
        sessions.seed(InterviewState().model_dump(), InterviewState().model_dump())

        found = await repository.list_all()

        assert len(found) == 2
        assert all(isinstance(state, InterviewState) for state in found)
