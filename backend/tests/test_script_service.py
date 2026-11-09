"""ScriptService: concorrência otimista na edição de roteiros (EV-03)."""

import pytest

from app.core.errors import ConflictError
from app.schemas.api import ScriptUpdate
from app.schemas.script import InterviewScript, Question
from app.services.script_service import ScriptService

pytestmark = pytest.mark.anyio


@pytest.fixture
def scripts_service(script_repository, session_repository) -> ScriptService:
    return ScriptService(script_repository, session_repository)


@pytest.fixture
async def stored(script_repository) -> InterviewScript:
    return await script_repository.create(
        InterviewScript(titulo="Transporte", perguntas=[Question(ordem=1, texto="Como vem?")])
    )


async def test_stale_copy_cannot_overwrite_a_newer_edit(
    scripts_service, script_repository, stored
):
    stale = await script_repository.get_or_raise(stored.script_id)
    newer = await script_repository.get_or_raise(stored.script_id)
    newer.titulo = "Editado por outra ação"
    await script_repository.save(newer)

    async def read_old_copy(_script_id):
        return stale  # a leitura do service chega com a cópia velha

    script_repository.get_or_raise = read_old_copy
    with pytest.raises(ConflictError, match="outra ação"):
        await scripts_service.update(stored.script_id, ScriptUpdate(tema="não pode vencer"))

    kept = await script_repository.get(stored.script_id)
    assert kept.titulo == "Editado por outra ação" and kept.tema == ""


async def test_sequential_updates_each_see_the_latest_version(scripts_service, stored):
    await scripts_service.update(stored.script_id, ScriptUpdate(titulo="v1"))
    second = await scripts_service.update(stored.script_id, ScriptUpdate(tema="v2"))

    assert (second.titulo, second.tema) == ("v1", "v2")
    assert second.versao == 2
