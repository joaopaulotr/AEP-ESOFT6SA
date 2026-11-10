import pytest

from app.db import collections
from app.db.demo_seed import build_demo_data, seed_demo
from app.schemas.interview import InterviewState
from app.schemas.participant import Participant
from app.schemas.script import DEFAULT_SCRIPT_ID, InterviewScript, Question
from app.schemas.synthesis import Synthesis

pytestmark = pytest.mark.anyio


@pytest.fixture
def data():
    return build_demo_data()


def test_builder_is_deterministic():
    assert build_demo_data() == build_demo_data()


def test_expected_volume(data):
    assert len(data.scripts) == 3
    assert len(data.participants) == 10
    assert len(data.sessions) == 14
    finished = [s for s in data.sessions if s.finished]
    assert len(finished) == 10
    assert len([s for s in data.syntheses if s.escopo == "sessao"]) == len(finished)
    assert len([s for s in data.syntheses if s.escopo == "roteiro"]) == 1
    assert any(s.origem.tipo == "upload" and s.origem.arquivo == "questionario-ubs.docx" for s in data.scripts)
    assert all(len(s.perguntas) in (4, 5) for s in data.scripts)
    assert sum(1 for s in data.sessions if s.participant_id is None) >= 1
    assert {p.canal for p in data.participants} == {"voz", "texto"}


def test_referential_integrity(data):
    script_ids = {s.script_id for s in data.scripts} | {DEFAULT_SCRIPT_ID}
    participant_ids = {p.participant_id for p in data.participants}
    sessions = {s.session_id: s for s in data.sessions}
    assert all(s.script_id in script_ids for s in data.sessions)
    assert all(s.participant_id in participant_ids for s in data.sessions if s.participant_id)
    for synthesis in data.syntheses:
        assert synthesis.script_id in script_ids
        if synthesis.escopo == "sessao":
            assert synthesis.session_id in sessions
            assert sessions[synthesis.session_id].finished
            assert synthesis.script_id == sessions[synthesis.session_id].script_id
            assert synthesis.synthesis_id == f"sessao:{synthesis.session_id}"
        else:
            assert synthesis.script_id != DEFAULT_SCRIPT_ID


def test_citations_are_literal_participant_quotes(data):
    sessions = {s.session_id: s for s in data.sessions}
    for synthesis in data.syntheses:
        assert synthesis.modelo == "demo"
        citations = [c for t in synthesis.temas for c in t.citacoes]
        assert citations and 2 <= len(synthesis.temas) <= 3 or synthesis.escopo == "roteiro"
        for citation in citations:
            participant_text = [
                t.text for t in sessions[citation.session_id].conversation if t.role == "participant"
            ]
            assert any(citation.texto in text for text in participant_text), citation.texto
    roteiro = next(s for s in data.syntheses if s.escopo == "roteiro")
    cited = {c.session_id for t in roteiro.temas for c in t.citacoes}
    assert len(cited) >= 3
    assert roteiro.sessoes_usadas == len(cited) and set(roteiro.sessoes_ids) == cited


def test_conversations_are_consistent(data):
    from app.db.seed import generalist_script

    scripts = {s.script_id: s for s in [*data.scripts, generalist_script()]}
    for session in data.sessions:
        script = scripts[session.script_id]
        ordens = {q.ordem for q in script.perguntas}
        turns = session.conversation
        assert turns[0].role == "interviewer" and turns[0].acao is None
        for turn in turns:
            if turn.role == "interviewer" and turn.acao is not None:
                assert 800 <= turn.latencia_ms <= 3500
        covered = {t.pergunta_ordem for t in turns if t.pergunta_ordem is not None}
        if session.finished:
            assert turns[-1].role == "interviewer"
            assert turns[-1].acao == "finish" and turns[-1].pergunta_ordem is None
            assert covered == ordens
            assert session.current_index == len(script.perguntas)
            assert session.asked_indices == list(range(len(script.perguntas)))
        else:
            assert session.current_index < len(script.perguntas)
            assert session.asked_indices == list(range(session.current_index))
            assert all(t.acao != "finish" for t in turns)
        timestamps = [t.timestamp for t in turns]
        assert timestamps == sorted(timestamps)
        assert session.metricas.tokens > 0


async def test_seed_round_trips_through_repositories(
    fake_db, script_repository, participant_repository, session_repository, synthesis_repository, data
):
    counts = await seed_demo(fake_db)
    assert counts == {
        collections.SCRIPTS: 3,
        collections.PARTICIPANTS: 10,
        collections.SESSIONS: 14,
        collections.SYNTHESES: 11,
    }
    assert await script_repository.count() == 4  # + generalista
    for script in data.scripts:
        assert await script_repository.get(script.script_id) == script
    for participant in data.participants:
        assert await participant_repository.get(participant.participant_id) == participant
    for session in data.sessions:
        loaded = await session_repository.get(session.session_id)
        assert isinstance(loaded, InterviewState) and loaded == session
        details = await session_repository.get_details(session.session_id)
        assert details.script is not None
        assert (details.participant is None) == (session.participant_id is None)
    for synthesis in data.syntheses:
        assert await synthesis_repository.get(synthesis.synthesis_id) == synthesis
    first = next(s for s in data.sessions if s.finished)
    assert (await synthesis_repository.get_for_session(first.session_id)) is not None


async def test_seed_is_idempotent(fake_db, session_repository, synthesis_repository):
    first = await seed_demo(fake_db)
    second = await seed_demo(fake_db)
    assert first == second
    assert await session_repository.count() == 14
    assert await synthesis_repository.count() == 11


async def test_reset_removes_only_demo_documents(
    fake_db, script_repository, session_repository, synthesis_repository, participant_repository
):
    await seed_demo(fake_db)
    real = InterviewState(session_id="sessao-real", script_id=DEFAULT_SCRIPT_ID)
    await session_repository.create(real)
    # Resquícios demo que o seed atual não regrava: só o reset de verdade os remove.
    await session_repository.create(InterviewState(session_id="demo-velha", script_id=DEFAULT_SCRIPT_ID))
    await synthesis_repository.save_for_session(
        Synthesis(escopo="sessao", session_id="demo-velha", script_id=DEFAULT_SCRIPT_ID, resumo="x")
    )
    await participant_repository.create(Participant(participant_id="demo-fantasma", apelido="Fantasma"))
    await script_repository.create(InterviewScript(script_id="demo-velho", titulo="Velho", perguntas=[Question(ordem=1, texto="Oi?")]))
    counts = await seed_demo(fake_db, reset=True)
    assert counts[collections.SESSIONS] == 14
    assert await session_repository.get("sessao-real") is not None
    assert await session_repository.get("demo-velha") is None
    assert await synthesis_repository.get_for_session("demo-velha") is None
    assert await participant_repository.get("demo-fantasma") is None
    assert await script_repository.get("demo-velho") is None
    assert await session_repository.count() == 15
    assert await script_repository.get(DEFAULT_SCRIPT_ID) is not None

    # reset sozinho em banco sem dados demo não falha e mantém dados reais
    await seed_demo(fake_db, reset=True)
    assert await session_repository.count() == 15
    assert await synthesis_repository.count() == 11
    assert await participant_repository.count() == 10


def test_script_synthesis_uses_the_fixed_id_the_api_reads(data):
    roteiro = next(s for s in data.syntheses if s.escopo == "roteiro")

    assert roteiro.synthesis_id == f"roteiro:{roteiro.script_id}"
