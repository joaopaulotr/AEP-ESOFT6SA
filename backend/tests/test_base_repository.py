"""BaseRepository[T]: CRUD genérico herdado pelos quatro repositórios (EV-02)."""

import pytest
from pydantic import BaseModel
from pymongo import ASCENDING, IndexModel

from app.core.errors import ConflictError, CorruptDocumentError, NotFoundError
from app.repositories.base import BaseRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.script_repository import ScriptRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.synthesis_repository import SynthesisRepository

pytestmark = pytest.mark.anyio


class Note(BaseModel):
    note_id: str
    texto: str
    tag: str = ""
    created_at: int = 0


class NoteRepository(BaseRepository[Note]):
    model = Note
    collection_name = "notes"
    id_field = "note_id"
    not_found_message = "Nota não encontrada."
    duplicate_message = "Nota repetida."
    extra_indexes = (IndexModel([("tag", ASCENDING)], name="tag"),)


@pytest.fixture
def notes(fake_db) -> NoteRepository:
    return NoteRepository(fake_db)


class TestStructure:
    def test_base_cannot_be_used_without_a_declared_collection(self, fake_db):
        with pytest.raises(TypeError, match="declarar model, collection_name e id_field"):
            BaseRepository(fake_db)

    def test_subclass_missing_the_id_field_is_rejected(self, fake_db):
        class Incomplete(BaseRepository[Note]):
            model = Note
            collection_name = "notes"

        with pytest.raises(TypeError):
            Incomplete(fake_db)

    @pytest.mark.parametrize(
        ("repository", "collection", "id_field"),
        [
            (ScriptRepository, "interview_scripts", "script_id"),
            (ParticipantRepository, "participants", "participant_id"),
            (SessionRepository, "interview_sessions", "session_id"),
            (SynthesisRepository, "syntheses", "synthesis_id"),
        ],
    )
    def test_each_aggregate_has_its_own_collection(self, fake_db, repository, collection, id_field):
        instance = repository(fake_db)

        assert isinstance(instance, BaseRepository)
        assert instance._collection.name == collection
        assert repository.id_field == id_field


class TestIndexes:
    async def test_identity_index_is_unique_and_extra_indexes_are_added(self, notes, fake_db):
        await notes.ensure_indexes()

        info = await fake_db["notes"].index_information()
        assert info["note_id_unico"]["unique"] is True
        assert "tag" in info

    async def test_ensure_indexes_is_idempotent(self, notes):
        await notes.ensure_indexes()
        await notes.ensure_indexes()


class TestCrud:
    async def test_create_then_get(self, notes):
        await notes.create(Note(note_id="a", texto="oi"))

        assert await notes.get("a") == Note(note_id="a", texto="oi")

    async def test_get_missing_returns_none(self, notes):
        assert await notes.get("x") is None

    async def test_get_or_raise_uses_the_aggregate_message(self, notes):
        with pytest.raises(NotFoundError, match="Nota não encontrada."):
            await notes.get_or_raise("x")

    async def test_duplicate_identity_becomes_conflict(self, notes):
        await notes.ensure_indexes()
        await notes.create(Note(note_id="a", texto="oi"))

        with pytest.raises(ConflictError, match="Nota repetida."):
            await notes.create(Note(note_id="a", texto="de novo"))

    async def test_mongo_id_never_leaks_into_the_model(self, notes, fake_db):
        await notes.create(Note(note_id="a", texto="oi"))

        raw = await fake_db["notes"].find_one({"note_id": "a"})
        assert "_id" in raw
        assert "_id" not in (await notes.get("a")).model_dump()

    async def test_save_updates_and_reports_missing(self, notes):
        await notes.create(Note(note_id="a", texto="oi"))

        assert await notes.save(Note(note_id="a", texto="editado")) is True
        assert (await notes.get("a")).texto == "editado"
        assert await notes.save(Note(note_id="nao-existe", texto="x")) is False
        assert await notes.get("nao-existe") is None

    async def test_save_that_breaks_a_unique_index_becomes_conflict(self, fake_db):
        repo = ScriptRepository(fake_db)
        await repo.ensure_indexes()
        from app.schemas.script import InterviewScript, Question

        first = InterviewScript(titulo="A", perguntas=[Question(ordem=1, texto="?")], slug_convite="a")
        second = InterviewScript(titulo="B", perguntas=[Question(ordem=1, texto="?")], slug_convite="b")
        await repo.create(first)
        await repo.create(second)

        second.slug_convite = "a"
        with pytest.raises(ConflictError, match="link de convite"):
            await repo.save(second)

    async def test_delete_reports_whether_something_was_removed(self, notes):
        await notes.create(Note(note_id="a", texto="oi"))

        assert await notes.delete("a") is True
        assert await notes.delete("a") is False

    async def test_exists_and_count(self, notes):
        await notes.create(Note(note_id="a", texto="oi", tag="x"))
        await notes.create(Note(note_id="b", texto="oi", tag="y"))

        assert await notes.exists("a") is True
        assert await notes.exists("z") is False
        assert await notes.count() == 2
        assert await notes.count({"tag": "x"}) == 1


class Versioned(BaseModel):
    doc_id: str
    texto: str = ""
    versao: int = 0


class VersionedRepository(BaseRepository[Versioned]):
    model = Versioned
    collection_name = "versioned"
    id_field = "doc_id"
    stale_message = "Versão velha."


class TestOptimisticLocking:
    async def test_each_save_bumps_the_version(self, fake_db):
        repo = VersionedRepository(fake_db)
        doc = await repo.create(Versioned(doc_id="a"))

        await repo.save(doc)
        await repo.save(doc)

        assert doc.versao == 2
        assert (await repo.get("a")).versao == 2

    async def test_stale_copy_is_rejected(self, fake_db):
        repo = VersionedRepository(fake_db)
        await repo.create(Versioned(doc_id="a"))
        first = await repo.get("a")
        second = await repo.get("a")

        first.texto = "primeira"
        await repo.save(first)
        second.texto = "velha"
        with pytest.raises(ConflictError, match="Versão velha."):
            await repo.save(second)
        assert (await repo.get("a")).texto == "primeira"

    async def test_document_without_version_field_is_saved(self, fake_db):
        await fake_db["versioned"].insert_one({"doc_id": "antigo", "texto": "x"})
        repo = VersionedRepository(fake_db)

        doc = await repo.get("antigo")
        assert await repo.save(doc) is True
        assert (await repo.get("antigo")).versao == 1

    async def test_missing_versioned_document_returns_false(self, fake_db):
        assert await VersionedRepository(fake_db).save(Versioned(doc_id="x")) is False


class TestCorruptDocuments:
    async def test_invalid_stored_document_raises_without_its_content(self, notes, fake_db):
        await fake_db["notes"].insert_one({"note_id": "a", "texto": {"fala": "Maria mora em SP"}})

        with pytest.raises(CorruptDocumentError) as error:
            await notes.get("a")
        assert "Maria" not in str(error.value)
        assert "notes" in str(error.value)


class TestList:
    async def test_filters_sorts_newest_first_and_paginates(self, notes):
        for index in range(5):
            await notes.create(Note(note_id=f"n{index}", texto="t", tag="par" if index % 2 == 0 else "impar", created_at=index))

        assert [n.note_id for n in await notes.list()] == ["n4", "n3", "n2", "n1", "n0"]
        assert [n.note_id for n in await notes.list({"tag": "par"})] == ["n4", "n2", "n0"]
        assert [n.note_id for n in await notes.list(limit=2, skip=1)] == ["n3", "n2"]

    async def test_empty_collection_returns_empty_list(self, notes):
        assert await notes.list() == []
