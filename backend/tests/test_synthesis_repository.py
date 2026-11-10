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


def script_report(script_id="r1", sessoes_ids=None, cited=None) -> Synthesis:
    from app.schemas.synthesis import Citation, Theme

    citacoes = [Citation(texto="fala citada aqui", session_id=c) for c in (cited or [])]
    return Synthesis(
        escopo="roteiro",
        script_id=script_id,
        resumo="Resumo derivado das falas.",
        temas=[Theme(tema="t", pontos=["ponto"], citacoes=citacoes)],
        divergencias=["divergência"],
        sessoes_ids=sessoes_ids or [],
    )


async def test_report_that_used_the_session_is_deleted_entirely(synthesis_repository):
    await synthesis_repository.save_for_script(script_report("r1", sessoes_ids=["a", "b"]))
    await synthesis_repository.save_for_script(script_report("r2", sessoes_ids=["c", "d"]))

    assert await synthesis_repository.delete_script_reports_with_session("a") == 1

    assert await synthesis_repository.get_for_script("r1") is None
    assert await synthesis_repository.get_for_script("r2") is not None


async def test_report_that_only_cites_the_session_is_deleted(synthesis_repository):
    await synthesis_repository.save_for_script(script_report("r1", cited=["a"]))
    assert await synthesis_repository.delete_script_reports_with_session("a", "r1") == 1


async def test_legacy_report_without_inputs_is_deleted_only_when_the_script_is_known(
    synthesis_repository, fake_db
):
    await synthesis_repository.save_for_script(script_report("r1"))
    await fake_db["syntheses"].update_one({"script_id": "r1"}, {"$unset": {"sessoes_ids": ""}})

    assert await synthesis_repository.delete_script_reports_with_session("a") == 0
    assert await synthesis_repository.delete_script_reports_with_session("a", "r2") == 0
    assert await synthesis_repository.delete_script_reports_with_session("a", "r1") == 1


async def test_report_metrics_are_incremented_and_survive_regeneration(synthesis_repository):
    from app.core.usage import UsageMeter

    await synthesis_repository.save_for_script(script_report("r1", sessoes_ids=["a"]))
    meter = UsageMeter(llm_input_tokens=100, llm_output_tokens=30)
    report_id = synthesis_repository.script_synthesis_id("r1")

    assert await synthesis_repository.add_metrics(report_id, meter, 0.5)
    await synthesis_repository.save_for_script(script_report("r1", sessoes_ids=["a"]))
    assert await synthesis_repository.add_metrics(report_id, meter, 0.25)

    saved = await synthesis_repository.get_for_script("r1")
    assert saved.metricas.custo_usd == 0.75 and saved.metricas.tokens == 260
    assert await synthesis_repository.add_metrics("roteiro:nao-existe", meter, 0.1) is False
    assert await synthesis_repository.add_metrics(report_id, UsageMeter(), 0.0) is True
