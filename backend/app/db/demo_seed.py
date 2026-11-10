"""Dados de demonstração (EV-08): entrevistas realistas sobre ODS 10.

`build_demo_data()` é puro e determinístico (sem I/O, ids e datas fixos).
`seed_demo()` grava tudo de forma idempotente; os ids de demonstração começam
com `demo-` (ou `sessao:demo-` nas sínteses de sessão), então `reset=True` nunca
encosta em dados reais.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db import collections
from app.db.demo_content import PARTICIPANTS, SESSION_SPECS, SYNTHESIS_SPECS
from app.db.seed import generalist_script
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.script_repository import ScriptRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.synthesis_repository import SynthesisRepository
from app.schemas.interview import InterviewState, SessionMetrics, Turn
from app.schemas.participant import Participant
from app.schemas.script import InterviewScript, Persona, Question, ScriptOrigin
from app.schemas.synthesis import Citation, Synthesis, Theme

BASE_DATE = datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc)
MODEL = "demo"  # texto escrito à mão, não gerado por IA
DEMO_PREFIX = "demo-"

CLOSING = (
    "Muito obrigada por dividir isso comigo. O que você contou é muito importante "
    "e vai ajudar a mostrar o que precisa melhorar. Encerramos por aqui."
)


@dataclass
class DemoData:
    scripts: list[InterviewScript] = field(default_factory=list)
    participants: list[Participant] = field(default_factory=list)
    sessions: list[InterviewState] = field(default_factory=list)
    syntheses: list[Synthesis] = field(default_factory=list)


def _at(days: int, hour: int, minute: int = 0) -> datetime:
    return BASE_DATE.replace(hour=hour, minute=minute) + timedelta(days=days)


# ---------------------------------------------------------------- roteiros


def _questions(items: list[tuple[str, str, int]]) -> list[Question]:
    return [
        Question(ordem=i, texto=texto, objetivo=objetivo, max_aprofundamentos=maximo)
        for i, (texto, objetivo, maximo) in enumerate(items, start=1)
    ]


def _scripts() -> list[InterviewScript]:
    transporte = InterviewScript(
        script_id="demo-transporte",
        titulo="Transporte público na periferia",
        tema="Mobilidade urbana e desigualdade",
        descricao="Como o ônibus e o deslocamento afetam trabalho, estudo e saúde de quem mora longe do centro.",
        perguntas=_questions(
            [
                ("Pra começar, me conta onde você mora e como é o seu deslocamento no dia a dia.", "Conhecer o contexto e a rotina de deslocamento.", 1),
                ("Pensa na última vez que você pegou ônibus: como foi essa viagem, do começo ao fim?", "Ouvir uma situação concreta e recente.", 2),
                ("O que mais pesa pra você nesse transporte hoje: tempo, preço, segurança, lotação?", "Descobrir a principal barreira percebida.", 2),
                ("Alguma vez esse transporte te impediu de fazer algo importante, como trabalhar, estudar ou ir ao médico?", "Identificar perdas concretas por falta de mobilidade.", 2),
                ("Se você pudesse mudar uma coisa no transporte do seu bairro, o que seria?", "Levantar a mudança desejada e o motivo.", 1),
            ]
        ),
        persona=Persona(nome="Ana", tom="acolhedor"),
        slug_convite="transporte-periferia",
        created_at=_at(-7, 14, 0),
        updated_at=_at(-7, 14, 0),
    )
    saude = InterviewScript(
        script_id="demo-saude",
        titulo="Acesso à saúde básica (UBS)",
        tema="Atendimento na atenção primária",
        descricao="Roteiro importado do questionário da secretaria de saúde sobre o uso das Unidades Básicas de Saúde.",
        origem=ScriptOrigin(tipo="upload", arquivo="questionario-ubs.docx", extraido_em=_at(-6, 10, 30)),
        perguntas=_questions(
            [
                ("Pra começar, me fala um pouco de você e de como você costuma cuidar da sua saúde.", "Conhecer a pessoa e seus hábitos de cuidado.", 1),
                ("Me conta a última vez que você precisou da UBS do seu bairro. O que aconteceu?", "Ouvir um uso concreto e recente do serviço.", 2),
                ("Como foi conseguir o atendimento: agendar, esperar, ser atendido?", "Mapear as etapas de acesso e espera.", 2),
                ("Teve alguma vez que você deixou de ir ou desistiu de ser atendido? Por quê?", "Entender as desistências e seus motivos.", 2),
                ("O que faria o atendimento da UBS ser melhor pra você e pra sua família?", "Levantar melhorias sugeridas pelo usuário.", 1),
            ]
        ),
        persona=Persona(nome="Marina", tom="acolhedor"),
        slug_convite="saude-basica-ubs",
        created_at=_at(-6, 10, 30),
        updated_at=_at(-6, 10, 30),
    )
    aplicativo = InterviewScript(
        script_id="demo-aplicativo",
        titulo="Trabalho por aplicativo",
        tema="Trabalho precarizado e direitos",
        descricao="A rotina, os ganhos e a falta de proteção de entregadores e motoristas de plataforma.",
        perguntas=_questions(
            [
                ("Me conta como é o seu trabalho por aplicativo e há quanto tempo você faz isso.", "Entender o perfil e a trajetória.", 1),
                ("Como foi o seu último dia de trabalho, desde a hora que você começou?", "Ouvir a rotina real, com horas e ganhos.", 2),
                ("O que mais te preocupa nesse tipo de trabalho: ganho, segurança, falta de direitos?", "Identificar riscos e inseguranças principais.", 2),
                ("Se pudesse mudar uma regra do aplicativo, qual seria?", "Levantar a mudança mais desejada.", 1),
            ]
        ),
        persona=Persona(nome="Davi", tom="neutro"),
        slug_convite="trabalho-por-aplicativo",
        created_at=_at(-5, 16, 0),
        updated_at=_at(-5, 16, 0),
    )
    return [transporte, saude, aplicativo]


# ----------------------------------------------------------------- sessões


def _build_session(
    *,
    number: int,
    script: InterviewScript,
    participant_id: str | None,
    canal: str,
    start: datetime,
    blocks: list,
    profile: dict[str, str],
) -> InterviewState:
    """Monta a sessão a partir de blocos por pergunta: [(fala, aprofundamento|None)].

    Aprofundamento None = o entrevistador avança (ou encerra, na última pergunta).
    """
    perguntas = script.perguntas
    total = len(perguntas)
    advanced = sum(1 for block in blocks if block and block[-1][1] is None)
    if len(blocks) > advanced + 1 or advanced > total:
        raise ValueError(f"demo-s{number:02d}: blocos inconsistentes")

    plan: list[tuple[str, str, int | None, str | None]] = [
        (
            "interviewer",
            f"Oi, eu sou {script.persona.nome}. Obrigada por aceitar conversar comigo, "
            f"não tem resposta certa nem errada. {perguntas[0].texto}",
            perguntas[0].ordem,
            None,
        )
    ]
    for index, block in enumerate(blocks):
        ordem = perguntas[index].ordem
        for answer, deepen in block:
            plan.append(("participant", answer, ordem, None))
            if deepen is not None:
                plan.append(("interviewer", deepen, ordem, "deepen"))
            elif index + 1 < total:
                proxima = perguntas[index + 1]
                plan.append(("interviewer", proxima.texto, proxima.ordem, "advance"))
            else:
                plan.append(("interviewer", CLOSING, None, "finish"))

    turns: list[Turn] = []
    moment = start
    words = 0
    for position, (role, text, ordem, acao) in enumerate(plan):
        latency: int | None = None
        if role == "participant":
            moment += timedelta(seconds=6 + int(len(text.split()) * 0.5))
            words += len(text.split())
        elif position > 0:
            latency = 800 + (position * 977 + number * 313) % 2701
            moment += timedelta(milliseconds=latency + 2500)
        turns.append(
            Turn(
                role=role,  # type: ignore[arg-type]
                text=text,
                timestamp=moment,
                pergunta_ordem=ordem,
                acao=acao,  # type: ignore[arg-type]
                latencia_ms=latency,
            )
        )

    tokens = 900 + int(words * 3.1)
    audio = round(words / 2.6, 1) if canal == "voz" else 0.0
    return InterviewState(
        session_id=f"demo-s{number:02d}",
        script_id=script.script_id,
        participant_id=participant_id,
        asked_indices=list(range(advanced)),
        current_index=advanced,
        conversation=turns,
        profile=profile,
        metricas=SessionMetrics(
            tokens=tokens,
            segundos_audio=audio,
            custo_usd=round(tokens * 0.0000009 + audio * 0.0001, 4),
        ),
        finished=advanced == total,
        created_at=start,
        updated_at=moment,
    )


def _sessions(scripts: dict[str, InterviewScript]) -> list[InterviewState]:
    canais = {pid: canal for pid, _, _, _, canal in PARTICIPANTS}
    return [
        _build_session(
            number=spec["n"],
            script=scripts[spec["script"]],
            participant_id=spec["participant"],
            canal=canais.get(spec["participant"], "voz"),
            start=_at(*spec["when"]),
            blocks=spec["blocks"],
            profile=spec["profile"],
        )
        for spec in SESSION_SPECS
    ]


# ------------------------------------------------------------------ sínteses


def _themes(raw: list) -> list[Theme]:
    return [
        Theme(
            tema=tema,
            pontos=pontos,
            citacoes=[Citation(session_id=sid, texto=texto) for sid, texto in citacoes],
        )
        for tema, pontos, citacoes in raw
    ]


def _syntheses(sessions: list[InterviewState]) -> list[Synthesis]:
    by_id = {s.session_id: s for s in sessions}
    result: list[Synthesis] = []
    for session_id, resumo, temas, lacunas in SYNTHESIS_SPECS["sessao"]:
        session = by_id[session_id]
        created = session.updated_at + timedelta(minutes=2)
        result.append(
            Synthesis(
                synthesis_id=SynthesisRepository.session_synthesis_id(session_id),
                escopo="sessao",
                script_id=session.script_id,
                session_id=session_id,
                resumo=resumo,
                temas=_themes(temas),
                lacunas=lacunas,
                modelo=MODEL,
                created_at=created,
                updated_at=created,
            )
        )
    script_id, resumo, temas, lacunas = SYNTHESIS_SPECS["roteiro"]
    created = _at(21, 9, 0)
    result.append(
        Synthesis(
            synthesis_id=SynthesisRepository.script_synthesis_id(script_id),
            escopo="roteiro",
            script_id=script_id,
            resumo=resumo,
            temas=_themes(temas),
            lacunas=lacunas,
            modelo=MODEL,
            created_at=created,
            updated_at=created,
        )
    )
    return result


# ------------------------------------------------------------------- público


def build_demo_data() -> DemoData:
    scripts = _scripts()
    sessions = _sessions({s.script_id: s for s in [*scripts, generalist_script()]})
    first_session: dict[str, datetime] = {}
    for session in sessions:
        if session.participant_id:
            first_session.setdefault(session.participant_id, session.created_at)
    participants = [
        Participant(
            participant_id=pid,
            apelido=apelido,
            faixa_etaria=faixa,
            regiao=regiao,
            canal=canal,
            created_at=first_session[pid] - timedelta(minutes=5),
            updated_at=first_session[pid] - timedelta(minutes=5),
        )
        for pid, apelido, faixa, regiao, canal in PARTICIPANTS
    ]
    return DemoData(
        scripts=scripts,
        participants=participants,
        sessions=sessions,
        syntheses=_syntheses(sessions),
    )


async def _upsert(repository: Any, entities: list) -> int:
    for entity in entities:
        await repository.upsert(entity)
    return len(entities)


async def seed_demo(database: Any, *, reset: bool = False) -> dict[str, int]:
    """Grava os dados de demonstração (idempotente). Devolve quantos documentos por coleção."""
    data = build_demo_data()
    scripts = ScriptRepository(database)
    participants = ParticipantRepository(database)
    sessions = SessionRepository(database)
    syntheses = SynthesisRepository(database)

    for repository in (scripts, participants, sessions, syntheses):
        await repository.ensure_indexes()
    await scripts.ensure_seed()

    if reset:
        await scripts.delete_by_id_prefix(DEMO_PREFIX)
        await participants.delete_by_id_prefix(DEMO_PREFIX)
        await sessions.delete_by_id_prefix(DEMO_PREFIX)
        await syntheses.delete_by_id_prefix(f"roteiro:{DEMO_PREFIX}")  # roteiro: roteiro:demo-...
        await syntheses.delete_by_id_prefix(f"sessao:{DEMO_PREFIX}")  # sessão: sessao:demo-...

    return {
        collections.SCRIPTS: await _upsert(scripts, data.scripts),
        collections.PARTICIPANTS: await _upsert(participants, data.participants),
        collections.SESSIONS: await _upsert(sessions, data.sessions),
        collections.SYNTHESES: await _upsert(syntheses, data.syntheses),
    }
