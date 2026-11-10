"""Integração com MongoDB real (EV-02): índices únicos, $lookup e agregações.

Rodam só com um Mongo disponível:
    MONGO_TEST_URI=mongodb://localhost:27017 pytest -m mongo
No CI, o workflow sobe um container mongo:7 e define MONGO_TEST_URI.
"""

import os
from uuid import uuid4

import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.errors import ConflictError
from app.db.seed import generalist_script
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.script_repository import ScriptRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.synthesis_repository import SynthesisRepository
from app.schemas.interview import InterviewState, Turn
from app.schemas.participant import Participant
from app.schemas.script import InterviewScript, Question
from app.schemas.synthesis import Synthesis

MONGO_TEST_URI = os.getenv("MONGO_TEST_URI")

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.mongo,
    pytest.mark.skipif(not MONGO_TEST_URI, reason="defina MONGO_TEST_URI para rodar contra um MongoDB real"),
]


@pytest.fixture
async def real_db():
    client = AsyncIOMotorClient(MONGO_TEST_URI, tz_aware=True, serverSelectionTimeoutMS=3000)
    name = f"aep_it_{uuid4().hex[:8]}"
    try:
        yield client[name]
    finally:
        await client.drop_database(name)
        client.close()


@pytest.fixture
async def repos(real_db):
    repositories = {
        "scripts": ScriptRepository(real_db),
        "participants": ParticipantRepository(real_db),
        "sessions": SessionRepository(real_db),
        "syntheses": SynthesisRepository(real_db),
    }
    for repository in repositories.values():
        await repository.ensure_indexes()
    await repositories["scripts"].ensure_seed()
    return repositories


async def test_indexes_exist_in_the_server(repos, real_db):
    sessions = await real_db["interview_sessions"].index_information()
    scripts = await real_db["interview_scripts"].index_information()

    assert sessions["session_id_unico"]["unique"] is True
    assert sessions["script_id_data"]["key"] == [("script_id", 1), ("created_at", -1)]
    assert scripts["slug_convite_unico"]["unique"] is True


async def test_unique_indexes_are_enforced(repos):
    state = InterviewState()
    await repos["sessions"].create(state)
    with pytest.raises(ConflictError):
        await repos["sessions"].create(state)

    with pytest.raises(ConflictError):
        await repos["scripts"].create(
            InterviewScript(titulo="Outro", slug_convite="generalista", perguntas=[Question(ordem=1, texto="?")])
        )


async def test_round_trip_keeps_timezone_and_nested_documents(repos):
    state = InterviewState(conversation=[Turn(role="interviewer", text="Oi", pergunta_ordem=1)])
    await repos["sessions"].create(state)

    found = await repos["sessions"].get(state.session_id)

    assert found.created_at.utcoffset().total_seconds() == 0
    assert found.conversation[0].pergunta_ordem == 1


async def test_lookup_joins_three_collections(repos):
    person = await repos["participants"].create(Participant(apelido="Zé"))
    with_person = await repos["sessions"].create(
        InterviewState(script_id=generalist_script().script_id, participant_id=person.participant_id)
    )
    anonymous = await repos["sessions"].create(InterviewState())

    joined = await repos["sessions"].get_details(with_person.session_id)
    alone = await repos["sessions"].get_details(anonymous.session_id)

    assert joined.participant.apelido == "Zé"
    assert joined.script.titulo == "Entrevista generalista"
    # No Mongo real, $lookup com participant_id nulo não pode trazer participante algum.
    assert alone.participant is None


async def test_one_synthesis_per_session(repos, real_db):
    for resumo in ("v1", "v2"):
        await repos["syntheses"].save_for_session(
            Synthesis(escopo="sessao", session_id="s1", script_id="entrevista-generalista", resumo=resumo)
        )

    assert await real_db["syntheses"].count_documents({"session_id": "s1"}) == 1


async def test_concurrent_synthesis_saves_never_duplicate(repos, real_db):
    import asyncio

    await asyncio.gather(
        *(
            repos["syntheses"].save_for_session(
                Synthesis(escopo="sessao", session_id="s1", script_id="entrevista-generalista", resumo=f"v{i}")
            )
            for i in range(10)
        )
    )

    assert await real_db["syntheses"].count_documents({"session_id": "s1"}) == 1


async def test_stale_session_copy_is_rejected(repos):
    state = await repos["sessions"].create(InterviewState())
    turn_copy = await repos["sessions"].get(state.session_id)
    finish_copy = await repos["sessions"].get(state.session_id)

    finish_copy.finished = True
    await repos["sessions"].save(finish_copy)

    with pytest.raises(ConflictError):
        await repos["sessions"].save(turn_copy)
    assert (await repos["sessions"].get(state.session_id)).finished is True


async def test_v010_sessions_are_backfilled(repos, real_db):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    await real_db["interview_sessions"].insert_one(
        {"session_id": "antiga", "asked_indices": [], "current_index": 4, "conversation": [],
         "profile": {}, "finished": True, "synthesis": "Relatório antigo.",
         "created_at": now, "updated_at": now}
    )

    assert await repos["sessions"].backfill_legacy(repos["syntheses"].import_legacy) == 1

    details = await repos["sessions"].get_details("antiga")
    assert details.script.script_id == "entrevista-generalista"
    assert (await repos["syntheses"].get_for_session("antiga")).resumo == "Relatório antigo."
    assert "synthesis" not in await real_db["interview_sessions"].find_one({"session_id": "antiga"})


async def test_session_delete_removes_the_script_report_that_used_it_on_real_mongo(repos, real_db):
    from app.schemas.synthesis import Citation, Theme

    syntheses = repos["syntheses"]
    used = Synthesis(
        escopo="roteiro", script_id="r1", resumo="derivado de a", sessoes_ids=["a", "b"],
        temas=[Theme(tema="t1", citacoes=[Citation(texto="fala de b", session_id="b")])],
    )
    cites = Synthesis(
        escopo="roteiro", script_id="r2", resumo="cita a",
        temas=[Theme(tema="t", citacoes=[Citation(texto="fala de a", session_id="a")])],
    )
    other = Synthesis(escopo="roteiro", script_id="r3", resumo="sem a", sessoes_ids=["c", "d"])
    for report in (used, cites, other):
        await syntheses.save_for_script(report)

    assert await syntheses.delete_script_reports_with_session("a") == 2

    assert await syntheses.get_for_script("r1") is None and await syntheses.get_for_script("r2") is None
    assert await syntheses.get_for_script("r3") is not None


@pytest.mark.parametrize("script_id", ["demo-transporte", "demo-saude", "demo-aplicativo"])
async def test_script_dashboard_on_real_mongo_matches_mongomock(real_db, script_id):
    """Painel do roteiro (EV-32): $lookup/$group no Mongo real = versão mongomock."""
    from datetime import datetime, timezone

    from app.db.demo_seed import seed_demo
    from tests.conftest import memory_db

    now = datetime(2026, 11, 10, 15, 0, tzinfo=timezone.utc)
    reference_db = memory_db()
    await seed_demo(reference_db)
    await seed_demo(real_db)

    results = []
    for database in (real_db, reference_db):
        script = await ScriptRepository(database).get_or_raise(script_id)
        results.append(await SessionRepository(database).script_dashboard(script, now=now))
    real, reference = results

    assert real.total_sessoes > 0
    assert real.model_dump() == reference.model_dump()
