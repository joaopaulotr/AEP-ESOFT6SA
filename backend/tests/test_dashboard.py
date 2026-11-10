"""Painel do roteiro (EV-32): agregações no banco conferidas contra cálculo manual."""

from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.db.demo_seed import build_demo_data, seed_demo
from app.main import app
from app.repositories.script_repository import ScriptRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.interview import InterviewState, SessionMetrics

pytestmark = pytest.mark.anyio

SP = ZoneInfo("America/Sao_Paulo")
NOW = datetime(2026, 11, 10, 15, 0, tzinfo=timezone.utc)


def _norm(tema: str) -> str:
    return " ".join(tema.split()).lower()


def _manual(script_id: str):
    data = build_demo_data()
    sessions = [s for s in data.sessions if s.script_id == script_id]
    script = next(s for s in data.scripts if s.script_id == script_id)
    return data, script, sessions


@pytest.fixture
async def seeded(fake_db):
    await seed_demo(fake_db)
    return fake_db


@pytest.mark.parametrize("script_id", ["demo-transporte", "demo-saude", "demo-aplicativo"])
async def test_numbers_match_manual_computation(seeded, script_id):
    data, script, sessions = _manual(script_id)
    stored = await ScriptRepository(seeded).get_or_raise(script_id)
    dash = await SessionRepository(seeded).script_dashboard(stored, now=NOW)

    done = [s for s in sessions if s.finished]
    assert dash.titulo == script.titulo
    assert dash.total_sessoes == len(sessions)
    assert dash.concluidas == len(done)
    assert dash.em_andamento == len(sessions) - len(done)
    assert dash.taxa_conclusao == round(len(done) / len(sessions), 3)
    minutes = [(s.updated_at - s.created_at).total_seconds() / 60 for s in done]
    assert dash.duracao_media_min == pytest.approx(sum(minutes) / len(minutes), abs=0.051)
    answers = [sum(t.role == "participant" for t in s.conversation) for s in sessions]
    assert dash.media_respostas == pytest.approx(sum(answers) / len(answers), abs=0.005)

    acoes = Counter(t.acao for s in sessions for t in s.conversation if t.acao)
    assert {a.acao: a.total for a in dash.acoes} == dict(acoes)

    for item, question in zip(dash.aprofundamentos_por_pergunta, script.perguntas):
        reached = [
            s for s in sessions if any(t.pergunta_ordem == question.ordem for t in s.conversation)
        ]
        counts = [
            sum(t.acao == "deepen" and t.pergunta_ordem == question.ordem for t in s.conversation)
            for s in reached
        ]
        expected = sum(counts) / len(counts) if counts else 0.0
        assert item.pergunta_ordem == question.ordem and item.texto == question.texto
        assert item.media == pytest.approx(expected, abs=0.051)
    assert len(dash.aprofundamentos_por_pergunta) == len(script.perguntas)

    costs = [s.metricas.custo_usd for s in sessions]
    assert dash.custo_total_usd == pytest.approx(sum(costs), abs=1e-6)
    paid = [c for c in costs if c > 0]
    assert dash.custo_medio_usd == pytest.approx(sum(paid) / len(paid), abs=1e-6)

    canais = {p.participant_id: p.canal for p in data.participants}
    expected_channels = Counter(canais.get(s.participant_id, "desconhecido") for s in sessions)
    assert {c.canal: c.total for c in dash.canais} == dict(expected_channels)

    days = Counter(s.created_at.astimezone(SP).date().isoformat() for s in sessions)
    assert {d.dia: d.total for d in dash.sessoes_por_dia} == dict(days)
    assert [d.dia for d in dash.sessoes_por_dia] == sorted(days)

    per_session: dict[str, set[str]] = {}
    for synthesis in data.syntheses:
        if synthesis.escopo == "sessao" and synthesis.script_id == script_id:
            per_session[synthesis.session_id] = {_norm(t.tema) for t in synthesis.temas}
    themes = Counter(tema for temas in per_session.values() for tema in temas)
    ranked = sorted(themes.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
    assert [(_norm(t.tema), t.sessoes) for t in dash.temas_mais_citados] == ranked


async def test_window_keeps_only_last_30_days(seeded):
    _, _, sessions = _manual("demo-transporte")
    stored = await ScriptRepository(seeded).get_or_raise("demo-transporte")
    last = max(s.created_at for s in sessions)
    late = last + timedelta(days=45)
    dash = await SessionRepository(seeded).script_dashboard(stored, now=late)
    assert dash.sessoes_por_dia == []
    assert dash.total_sessoes == len(sessions)  # a janela só vale para o gráfico por dia


async def test_day_uses_sao_paulo_timezone(fake_db):
    sessions = SessionRepository(fake_db)
    await sessions.ensure_indexes()
    scripts = ScriptRepository(fake_db)
    await scripts.ensure_seed()
    script = await scripts.get_or_raise("entrevista-generalista")
    # 01:30 UTC de 11/11 ainda é 22:30 de 10/11 em São Paulo
    moment = datetime(2026, 11, 11, 1, 30, tzinfo=timezone.utc)
    await sessions.create(
        InterviewState(
            session_id="s-tz", script_id=script.script_id, created_at=moment, updated_at=moment
        )
    )
    dash = await sessions.script_dashboard(script, now=moment)
    assert [(d.dia, d.total) for d in dash.sessoes_por_dia] == [("2026-11-10", 1)]


async def test_themes_normalize_case_spaces_and_count_distinct_sessions(seeded):
    from app.repositories.synthesis_repository import SynthesisRepository
    from app.schemas.synthesis import Synthesis, Theme

    syntheses = SynthesisRepository(seeded)
    _, _, sessions = _manual("demo-transporte")
    ids = [s.session_id for s in sessions][:3]
    variants = ["Tempo  de espera", "tempo de espera ", "TEMPO DE ESPERA"]
    for session_id, tema in zip(ids, variants):
        await syntheses.upsert(
            Synthesis(
                synthesis_id=f"sessao:{session_id}",
                escopo="sessao",
                script_id="demo-transporte",
                session_id=session_id,
                resumo="r",
                temas=[Theme(tema=tema, pontos=[]), Theme(tema=tema.upper(), pontos=[])],
                modelo="t",
            )
        )
    stored = await ScriptRepository(seeded).get_or_raise("demo-transporte")
    dash = await SessionRepository(seeded).script_dashboard(stored, now=NOW)
    top = dash.temas_mais_citados[0]
    assert (_norm(top.tema), top.sessoes) == ("tempo de espera", 3)  # 3 sessões, não 6 menções
    assert len(dash.temas_mais_citados) <= 8


async def test_empty_script_is_all_zeros(fake_db):
    scripts = ScriptRepository(fake_db)
    await scripts.ensure_seed()
    script = await scripts.get_or_raise("entrevista-generalista")
    dash = await SessionRepository(fake_db).script_dashboard(script, now=NOW)
    assert dash.total_sessoes == dash.concluidas == dash.em_andamento == 0
    assert dash.taxa_conclusao == dash.duracao_media_min == dash.media_respostas == 0
    assert dash.custo_total_usd == dash.custo_medio_usd == 0
    assert dash.acoes == dash.temas_mais_citados == dash.sessoes_por_dia == dash.canais == []
    assert len(dash.aprofundamentos_por_pergunta) == len(script.perguntas)
    assert all(q.media == 0 for q in dash.aprofundamentos_por_pergunta)


async def test_sessions_without_cost_keep_average_at_zero(fake_db):
    scripts = ScriptRepository(fake_db)
    await scripts.ensure_seed()
    script = await scripts.get_or_raise("entrevista-generalista")
    sessions = SessionRepository(fake_db)
    await sessions.ensure_indexes()
    await sessions.create(InterviewState(session_id="a", script_id=script.script_id))
    await sessions.create(
        InterviewState(
            session_id="b", script_id=script.script_id, metricas=SessionMetrics(custo_usd=0.5)
        )
    )
    dash = await sessions.script_dashboard(script)
    assert dash.custo_total_usd == 0.5 and dash.custo_medio_usd == 0.5
    assert dash.canais[0].canal == "desconhecido" and dash.canais[0].total == 2


class TestRoute:
    @pytest.fixture(autouse=True)
    def _fake_llm(self, monkeypatch):
        monkeypatch.setattr(deps.settings, "llm_provider", "fake")  # nunca a OpenAI real

    def test_unknown_script_is_404(self):
        with TestClient(app) as client:
            response = client.get("/api/v1/scripts/nao-existe/painel")
        assert response.status_code == 404

    def test_empty_script_returns_the_contract(self):
        with TestClient(app) as client:
            response = client.get("/api/v1/scripts/entrevista-generalista/painel")
        body = response.json()
        assert response.status_code == 200
        assert body["script_id"] == "entrevista-generalista" and body["total_sessoes"] == 0
        assert set(body) == {
            "script_id", "titulo", "total_sessoes", "concluidas", "em_andamento", "taxa_conclusao",
            "duracao_media_min", "media_respostas", "acoes", "aprofundamentos_por_pergunta",
            "custo_total_usd", "custo_medio_usd", "temas_mais_citados", "sessoes_por_dia", "canais",
        }

    async def test_seeded_script_over_http(self, seeded):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
            response = await client.get("/api/v1/scripts/demo-saude/painel")
        _, _, sessions = _manual("demo-saude")
        assert response.status_code == 200
        assert response.json()["total_sessoes"] == len(sessions)
