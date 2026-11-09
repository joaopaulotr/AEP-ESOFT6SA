import pytest

from app.schemas.synthesis import Synthesis

pytestmark = pytest.mark.anyio


def session_synthesis(session_id="s1", resumo="r", script_id="roteiro") -> Synthesis:
    return Synthesis(escopo="sessao", session_id=session_id, script_id=script_id, resumo=resumo)


async def test_save_for_session_creates_then_replaces(synthesis_repository, fake_db):
    await synthesis_repository.save_for_session(session_synthesis(resumo="primeira"))
    first = await synthesis_repository.get_for_session("s1")  # datas do Mongo têm precisão de ms
    second = await synthesis_repository.save_for_session(session_synthesis(resumo="segunda"))

    assert second.synthesis_id == first.synthesis_id
    assert second.created_at == first.created_at
    assert await fake_db["syntheses"].count_documents({}) == 1
    assert (await synthesis_repository.get_for_session("s1")).resumo == "segunda"


async def test_get_for_session_ignores_script_scope(synthesis_repository):
    await synthesis_repository.create(Synthesis(escopo="roteiro", script_id="roteiro", resumo="geral"))

    assert await synthesis_repository.get_for_session("s1") is None


async def test_list_for_script_includes_both_scopes(synthesis_repository):
    await synthesis_repository.save_for_session(session_synthesis("a"))
    await synthesis_repository.save_for_session(session_synthesis("b"))
    await synthesis_repository.create(Synthesis(escopo="roteiro", script_id="roteiro", resumo="geral"))
    await synthesis_repository.save_for_session(session_synthesis("c", script_id="outro"))

    found = await synthesis_repository.list_for_script("roteiro")

    assert sorted(s.escopo for s in found) == ["roteiro", "sessao", "sessao"]


async def test_session_synthesis_id_is_deterministic(synthesis_repository):
    saved = await synthesis_repository.save_for_session(session_synthesis("abc"))

    assert saved.synthesis_id == "sessao:abc"


async def test_concurrent_saves_keep_a_single_document(synthesis_repository, fake_db):
    import anyio

    await synthesis_repository.ensure_indexes()
    async with anyio.create_task_group() as group:
        for resumo in ("a", "b", "c"):
            group.start_soon(synthesis_repository.save_for_session, session_synthesis(resumo=resumo))

    assert await fake_db["syntheses"].count_documents({"session_id": "s1"}) == 1


async def test_save_for_session_rejects_script_scope(synthesis_repository):
    with pytest.raises(ValueError, match="só aceita síntese de sessão"):
        await synthesis_repository.save_for_session(
            Synthesis(escopo="roteiro", script_id="roteiro", resumo="geral")
        )


async def test_import_legacy_keeps_the_old_text_without_overwriting(synthesis_repository):
    await synthesis_repository.import_legacy("antiga", "texto da v0.1.0")
    await synthesis_repository.import_legacy("antiga", "outro texto")

    stored = await synthesis_repository.get_for_session("antiga")
    assert (stored.resumo, stored.modelo, stored.synthesis_id) == ("texto da v0.1.0", "v0.1.0", "sessao:antiga")


def test_declares_reference_indexes(synthesis_repository):
    names = {index.document["name"] for index in synthesis_repository.indexes()}

    assert names == {"synthesis_id_unico", "session_id", "script_id_escopo"}
