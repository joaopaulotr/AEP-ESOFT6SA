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


async def test_script_stats_pipeline(repos):
    def turn(acao, ordem, role="interviewer"):
        return Turn(role=role, text="x", acao=acao, pergunta_ordem=ordem)

    await repos["sessions"].create(
        InterviewState(
            finished=True,
            conversation=[turn(None, 1), turn(None, 1, "participant"), turn("deepen", 1),
                          turn(None, 1, "participant"), turn("advance", 2), turn(None, 2, "participant"),
                          turn("finish", 2)],
        )
    )
    await repos["sessions"].create(InterviewState(conversation=[turn(None, 1)]))

    stats = await repos["sessions"].script_stats("entrevista-generalista")

    assert (stats.total_sessoes, stats.concluidas, stats.taxa_conclusao) == (2, 1, 0.5)
    assert stats.media_respostas == 1.5
    assert {a.acao: a.total for a in stats.acoes} == {"advance": 1, "deepen": 1, "finish": 1}
    assert [(q.pergunta_ordem, q.media_aprofundamentos) for q in stats.aprofundamentos_por_pergunta] == [
        (1, 0.5),
        (2, 0.0),
    ]


async def test_one_synthesis_per_session(repos, real_db):
    for resumo in ("v1", "v2"):
        await repos["syntheses"].save_for_session(
            Synthesis(escopo="sessao", session_id="s1", script_id="entrevista-generalista", resumo=resumo)
        )

    assert await real_db["syntheses"].count_documents({"session_id": "s1"}) == 1
