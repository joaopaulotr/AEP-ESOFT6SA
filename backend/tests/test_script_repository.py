import pytest

from app.core.errors import ConflictError
from app.schemas.script import DEFAULT_SCRIPT_ID, InterviewScript, Question

pytestmark = pytest.mark.anyio


def make_script(titulo="Saúde", slug="", ativo=True) -> InterviewScript:
    return InterviewScript(
        titulo=titulo, slug_convite=slug, ativo=ativo, perguntas=[Question(ordem=1, texto="Como vai?")]
    )


class TestSeed:
    async def test_inserts_the_generalist_script_once(self, script_repository, fake_db):
        first = await script_repository.ensure_seed()
        second = await script_repository.ensure_seed()

        assert first.script_id == second.script_id == DEFAULT_SCRIPT_ID
        assert await fake_db["interview_scripts"].count_documents({}) == 1

    async def test_does_not_overwrite_an_edited_seed(self, script_repository):
        seed = await script_repository.ensure_seed()
        seed.titulo = "Generalista (editado)"
        await script_repository.save(seed)

        again = await script_repository.ensure_seed()

        assert again.titulo == "Generalista (editado)"

    async def test_get_default_creates_the_seed_when_missing(self, script_repository):
        default = await script_repository.get_default()

        assert default.script_id == DEFAULT_SCRIPT_ID
        assert await script_repository.exists(DEFAULT_SCRIPT_ID)

    async def test_nested_questions_are_stored_as_subdocuments(self, script_repository, fake_db):
        await script_repository.ensure_seed()

        raw = await fake_db["interview_scripts"].find_one({"script_id": DEFAULT_SCRIPT_ID})

        assert isinstance(raw["perguntas"], list) and len(raw["perguntas"]) == 4
        assert set(raw["perguntas"][0]) == {"ordem", "texto", "objetivo", "max_aprofundamentos"}


class TestQueries:
    async def test_get_by_slug(self, script_repository):
        script = await script_repository.create(make_script(slug="saude-2026"))

        assert (await script_repository.get_by_slug("saude-2026")).script_id == script.script_id
        assert await script_repository.get_by_slug("nao-existe") is None

    async def test_list_active_skips_inactive_scripts(self, script_repository):
        active = await script_repository.create(make_script("Ativo"))
        await script_repository.create(make_script("Inativo", ativo=False))

        assert [s.script_id for s in await script_repository.list_active()] == [active.script_id]

    async def test_invite_slug_is_unique(self, script_repository):
        await script_repository.ensure_indexes()
        await script_repository.create(make_script(slug="convite"))

        with pytest.raises(ConflictError, match="link de convite"):
            await script_repository.create(make_script(slug="convite"))
