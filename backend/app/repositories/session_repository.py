from collections import Counter
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from collections.abc import Awaitable, Callable

from pymongo import ASCENDING, DESCENDING, IndexModel

from app.core.usage import UsageMeter
from app.db import collections
from app.repositories.base import BaseRepository
from app.schemas.api import (
    ActionTotal,
    ChannelCount,
    DayCount,
    QuestionDeepeningAvg,
    ScriptDashboard,
    SessionSummary,
    ThemeCount,
)
from app.schemas.interview import (
    ActionCount,
    InterviewState,
    QuestionDeepening,
    ScriptStats,
    SessionDetails,
)
from app.schemas.participant import Participant
from app.schemas.script import DEFAULT_SCRIPT_ID, InterviewScript

DASHBOARD_TIMEZONE = "America/Sao_Paulo"
DASHBOARD_DAYS = 30
DASHBOARD_TOP_THEMES = 8
CANAL_DESCONHECIDO = "desconhecido"

LegacySynthesisHandler = Callable[[str, str], Awaitable[None]]  # (session_id, texto)


class SessionRepository(BaseRepository[InterviewState]):
    model = InterviewState
    collection_name = collections.SESSIONS
    id_field = "session_id"
    not_found_message = "Sessão não encontrada."
    duplicate_message = "Sessão já existe."
    stale_message = "A sessão foi alterada por outra ação. Tente de novo."
    save_exclude = ("metricas",)  # só muda por add_metrics ($inc), nunca por cópia velha
    extra_indexes = (
        IndexModel([("script_id", ASCENDING), ("created_at", DESCENDING)], name="script_id_data"),
        IndexModel([("script_id", ASCENDING), ("updated_at", DESCENDING)], name="script_id_atualizada"),
        IndexModel([("participant_id", ASCENDING)], name="participant_id"),
    )

    async def add_metrics(self, session_id: str, meter: UsageMeter, cost: float) -> bool:
        """Soma o consumo da operação nas métricas com $inc atômico (sem tocar em `versao`).
        Devolve False se a sessão não existe (apagada no meio)."""
        if meter.is_empty:
            return await self.exists(session_id)
        increments = {
            "metricas.llm_input_tokens": meter.llm_input_tokens,
            "metricas.llm_output_tokens": meter.llm_output_tokens,
            "metricas.stt_seconds": meter.stt_seconds,
            "metricas.tts_chars": meter.tts_chars,
            "metricas.tokens": meter.llm_input_tokens + meter.llm_output_tokens,
            "metricas.segundos_audio": meter.stt_seconds,
            "metricas.custo_usd": cost,
        }
        result = await self._collection.update_one({self.id_field: session_id}, {"$inc": increments})
        return result.matched_count > 0

    async def list_by_script(self, script_id: str, *, limit: int = 100) -> list[InterviewState]:
        return await self.list({"script_id": script_id}, limit=limit)

    async def count_by_script(self, script_ids: list[str]) -> dict[str, tuple[int, int]]:
        """script_id -> (total, concluídas) dos roteiros pedidos, numa só agregação."""
        rows = await self._collection.aggregate(
            [
                {"$match": {"script_id": {"$in": script_ids}}},
                {
                    "$group": {
                        "_id": "$script_id",
                        "total": {"$sum": 1},
                        "concluidas": {"$sum": {"$cond": ["$finished", 1, 0]}},
                    }
                }
            ]
        ).to_list(length=None)
        return {row["_id"]: (row["total"], row["concluidas"]) for row in rows}

    async def has_for_script(self, script_id: str) -> bool:
        return await self.count({"script_id": script_id}) > 0

    async def has_for_participant(self, participant_id: str) -> bool:
        return await self.count({"participant_id": participant_id}) > 0

    async def list_summaries(
        self, script_id: str, *, status: str | None = None, limit: int = 50
    ) -> list[SessionSummary]:
        """Sessões do roteiro, mais recentes primeiro, com o apelido do participante e a
        existência de síntese resolvidos por $lookup (sem consulta extra por sessão)."""
        match: dict = {"script_id": script_id}
        if status is not None:
            match["status"] = status
        pipeline = [
            {"$match": match},
            {"$sort": {"updated_at": -1, "session_id": 1}},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": collections.PARTICIPANTS,
                    "localField": "participant_id",
                    "foreignField": "participant_id",
                    "as": "participante_doc",
                }
            },
            {
                "$lookup": {
                    "from": collections.SYNTHESES,
                    "localField": "session_id",
                    "foreignField": "session_id",
                    "as": "sinteses",
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "session_id": 1,
                    "script_id": 1,
                    "participant_id": 1,
                    "status": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "participante_doc.apelido": 1,
                    "respostas": {
                        "$size": {
                            "$filter": {
                                "input": {"$ifNull": ["$conversation", []]},
                                "as": "turno",
                                "cond": {"$eq": ["$$turno.role", "participant"]},
                            }
                        }
                    },
                    "tem_sintese": {
                        "$gt": [
                            {
                                "$size": {
                                    "$filter": {
                                        "input": "$sinteses",
                                        "as": "s",
                                        "cond": {"$eq": ["$$s.escopo", "sessao"]},
                                    }
                                }
                            },
                            0,
                        ]
                    },
                }
            },
        ]
        summaries = []
        for document in await self._collection.aggregate(pipeline).to_list(length=limit):
            owner = document.pop("participante_doc", None) or []
            document["participante"] = owner[0].get("apelido") if owner else None
            summaries.append(self._validate(SessionSummary, document, self.collection_name))
        return summaries

    async def list_by_participant(
        self, participant_id: str, *, limit: int = 100
    ) -> list[InterviewState]:
        return await self.list({"participant_id": participant_id}, limit=limit)

    # -- migração da v0.1.0 -------------------------------------------------

    async def backfill_legacy(self, on_synthesis: LegacySynthesisHandler) -> int:
        """Completa no banco as sessões gravadas pela v0.1.0 (idempotente).

        Elas não têm script_id/status/versao, então ficariam fora do $lookup e das
        agregações. A síntese antiga (campo `synthesis`) é entregue a `on_synthesis`
        antes de ser removida do documento. Devolve quantas sessões foram migradas.
        """
        # Não valida o documento inteiro: a v0.1.0 podia gravar perfil fora do modelo
        # (RK-07), e um documento ruim não pode derrubar o startup. Só os campos usados.
        legacy = await self._collection.find(
            {"script_id": {"$exists": False}},
            {"session_id": 1, "finished": 1, "synthesis": 1},
        ).to_list(length=None)
        now = datetime.now(timezone.utc)
        for document in legacy:
            session_id = document["session_id"]
            old_synthesis = document.get("synthesis")
            if isinstance(old_synthesis, str) and old_synthesis.strip():
                await on_synthesis(session_id, old_synthesis)  # antes do $unset
            await self._collection.update_one(
                {"session_id": session_id, "script_id": {"$exists": False}},
                {
                    "$set": {
                        "script_id": DEFAULT_SCRIPT_ID,
                        "participant_id": None,
                        "status": "concluida" if document.get("finished") else "em_andamento",
                        "versao": 0,
                    },
                    "$unset": {"synthesis": ""},
                },
            )
            # Sem datas, a sessão não valida em SessionSummary nem ordena na listagem.
            for date_field in ("created_at", "updated_at"):
                await self._collection.update_one(
                    {"session_id": session_id, date_field: {"$exists": False}},
                    {"$set": {date_field: now}},
                )
        return len(legacy)

    # -- consultas relacionais ($lookup) ----------------------------------

    async def get_details(self, session_id: str) -> SessionDetails | None:
        """Sessão + roteiro + participante numa única consulta."""
        pipeline = [
            {"$match": {"session_id": session_id}},
            {
                "$lookup": {
                    "from": collections.SCRIPTS,
                    "localField": "script_id",
                    "foreignField": "script_id",
                    "as": "script",
                }
            },
            {
                "$lookup": {
                    "from": collections.PARTICIPANTS,
                    "localField": "participant_id",
                    "foreignField": "participant_id",
                    "as": "participant",
                }
            },
            {"$unwind": {"path": "$script", "preserveNullAndEmptyArrays": True}},
            {"$unwind": {"path": "$participant", "preserveNullAndEmptyArrays": True}},
            {"$project": {"_id": 0, "script._id": 0, "participant._id": 0}},
            {"$limit": 1},
        ]
        documents = await self._collection.aggregate(pipeline).to_list(length=1)
        if not documents:
            return None
        document = documents[0]
        script = document.pop("script", None)
        participant = document.pop("participant", None)
        return SessionDetails(
            session=self._to_model(document),
            script=self._validate(InterviewScript, script, collections.SCRIPTS) if script else None,
            participant=(
                self._validate(Participant, participant, collections.PARTICIPANTS)
                if participant
                else None
            ),
        )

    # -- agregações (base do dashboard, EV-32) ----------------------------

    async def script_stats(self, script_id: str) -> ScriptStats:
        match = {"$match": {"script_id": script_id}}

        summary = await self._collection.aggregate(
            [
                match,
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": 1},
                        "concluidas": {"$sum": {"$cond": ["$finished", 1, 0]}},
                        "media_respostas": {
                            "$avg": {
                                "$size": {
                                    "$filter": {
                                        "input": "$conversation",
                                        "as": "turno",
                                        "cond": {"$eq": ["$$turno.role", "participant"]},
                                    }
                                }
                            }
                        },
                    }
                },
            ]
        ).to_list(length=1)
        if not summary:
            return ScriptStats(script_id=script_id)

        actions = await self._collection.aggregate(
            [
                match,
                {"$unwind": "$conversation"},
                {"$match": {"conversation.acao": {"$in": ["deepen", "advance", "finish"]}}},
                {"$group": {"_id": "$conversation.acao", "total": {"$sum": 1}}},
                {"$sort": {"_id": 1}},
            ]
        ).to_list(length=None)

        deepening = await self._collection.aggregate(
            [
                match,
                {"$unwind": "$conversation"},
                {"$match": {"conversation.pergunta_ordem": {"$ne": None}}},
                {
                    "$group": {
                        "_id": {
                            "session_id": "$session_id",
                            "ordem": "$conversation.pergunta_ordem",
                        },
                        "aprofundamentos": {
                            "$sum": {"$cond": [{"$eq": ["$conversation.acao", "deepen"]}, 1, 0]}
                        },
                    }
                },
                {"$group": {"_id": "$_id.ordem", "media": {"$avg": "$aprofundamentos"}}},
                {"$sort": {"_id": 1}},
            ]
        ).to_list(length=None)

        total = summary[0]["total"]
        concluidas = summary[0]["concluidas"]
        return ScriptStats(
            script_id=script_id,
            total_sessoes=total,
            concluidas=concluidas,
            taxa_conclusao=round(concluidas / total, 4) if total else 0.0,
            media_respostas=round(summary[0]["media_respostas"] or 0.0, 2),
            acoes=[ActionCount(acao=item["_id"], total=item["total"]) for item in actions],
            aprofundamentos_por_pergunta=[
                QuestionDeepening(pergunta_ordem=item["_id"], media_aprofundamentos=round(item["media"], 2))
                for item in deepening
            ],
        )

    # -- painel do roteiro (EV-32) ----------------------------------------

    async def script_dashboard(
        self, script: InterviewScript, *, now: datetime | None = None
    ) -> ScriptDashboard:
        """Um `$facet` por grupo de números, tudo calculado no banco.

        O dia (fuso America/Sao_Paulo) é agrupado em Python: o `$dateToString` com
        `timezone` não existe no mongomock dos testes, e assim há um só caminho de
        código para o Mongo real e para os testes. O banco só devolve as datas da
        janela dos últimos 30 dias (uma por sessão); só aparecem dias com sessões."""
        zone = ZoneInfo(DASHBOARD_TIMEZONE)
        today = (now or datetime.now(timezone.utc)).astimezone(zone).date()
        first_day = today - timedelta(days=DASHBOARD_DAYS - 1)
        window_start = datetime.combine(first_day, time.min, tzinfo=zone).astimezone(timezone.utc)

        def lookup(source: str, local: str, foreign: str, alias: str) -> dict:
            return {"$lookup": {"from": source, "localField": local, "foreignField": foreign, "as": alias}}

        done = {"$eq": ["$status", "concluida"]}
        cost = {"$ifNull": ["$metricas.custo_usd", 0]}
        pipeline = [
            {"$match": {"script_id": script.script_id}},
            {
                "$facet": {
                    "resumo": [
                        {
                            "$group": {
                                "_id": None,
                                "total": {"$sum": 1},
                                "concluidas": {"$sum": {"$cond": [done, 1, 0]}},
                                "respostas": {
                                    "$avg": {
                                        "$size": {
                                            "$filter": {
                                                "input": {"$ifNull": ["$conversation", []]},
                                                "as": "turno",
                                                "cond": {"$eq": ["$$turno.role", "participant"]},
                                            }
                                        }
                                    }
                                },
                                "duracao_ms": {
                                    "$sum": {
                                        "$cond": [done, {"$subtract": ["$updated_at", "$created_at"]}, 0]
                                    }
                                },
                                "custo": {"$sum": cost},
                                "com_custo": {"$sum": {"$cond": [{"$gt": [cost, 0]}, 1, 0]}},
                            }
                        }
                    ],
                    "acoes": [
                        {"$unwind": "$conversation"},
                        {"$match": {"conversation.acao": {"$in": ["deepen", "advance", "finish"]}}},
                        {"$group": {"_id": "$conversation.acao", "total": {"$sum": 1}}},
                        {"$sort": {"_id": 1}},
                    ],
                    "aprofundamentos": [
                        {"$unwind": "$conversation"},
                        {"$match": {"conversation.pergunta_ordem": {"$ne": None}}},
                        {
                            "$group": {
                                "_id": {"s": "$session_id", "o": "$conversation.pergunta_ordem"},
                                "n": {"$sum": {"$cond": [{"$eq": ["$conversation.acao", "deepen"]}, 1, 0]}},
                            }
                        },
                        {"$group": {"_id": "$_id.o", "media": {"$avg": "$n"}}},
                    ],
                    "canais": [
                        lookup(collections.PARTICIPANTS, "participant_id", "participant_id", "dono"),
                        {
                            "$project": {
                                "canal": {"$ifNull": [{"$arrayElemAt": ["$dono.canal", 0]}, CANAL_DESCONHECIDO]}
                            }
                        },
                        {"$group": {"_id": "$canal", "total": {"$sum": 1}}},
                    ],
                    "datas": [
                        {"$match": {"created_at": {"$gte": window_start}}},
                        {"$project": {"_id": 0, "created_at": 1}},
                    ],
                    "temas": [
                        lookup(collections.SYNTHESES, "session_id", "session_id", "sinteses"),
                        {"$project": {"_id": 0, "sinteses.escopo": 1, "sinteses.temas.tema": 1}},
                    ],
                }
            },
        ]
        facets = (await self._collection.aggregate(pipeline).to_list(length=1))[0]

        resumo = facets["resumo"][0] if facets["resumo"] else None
        total = resumo["total"] if resumo else 0
        concluidas = resumo["concluidas"] if resumo else 0
        deepening = {item["_id"]: item["media"] for item in facets["aprofundamentos"]}

        days: Counter = Counter()
        for doc in facets["datas"]:
            moment = doc["created_at"]
            moment = moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
            day = moment.astimezone(zone).date()
            if first_day <= day <= today:
                days[day] += 1

        return ScriptDashboard(
            script_id=script.script_id,
            titulo=script.titulo,
            total_sessoes=total,
            concluidas=concluidas,
            em_andamento=total - concluidas,
            taxa_conclusao=round(concluidas / total, 3) if total else 0.0,
            duracao_media_min=round(resumo["duracao_ms"] / concluidas / 60000, 1) if concluidas else 0.0,
            media_respostas=round(resumo["respostas"] or 0.0, 2) if resumo else 0.0,
            acoes=[ActionTotal(acao=item["_id"], total=item["total"]) for item in facets["acoes"]],
            aprofundamentos_por_pergunta=[
                QuestionDeepeningAvg(
                    pergunta_ordem=q.ordem, texto=q.texto, media=round(deepening.get(q.ordem, 0.0), 1)
                )
                for q in script.perguntas
            ],
            custo_total_usd=round(resumo["custo"], 6) if resumo else 0.0,
            custo_medio_usd=(
                round(resumo["custo"] / resumo["com_custo"], 6) if resumo and resumo["com_custo"] else 0.0
            ),
            temas_mais_citados=self._top_themes(facets["temas"]),
            sessoes_por_dia=[DayCount(dia=d.isoformat(), total=n) for d, n in sorted(days.items())],
            canais=[
                ChannelCount(canal=item["_id"], total=item["total"])
                for item in sorted(facets["canais"], key=lambda c: (-c["total"], c["_id"]))
            ],
        )

    @staticmethod
    def _top_themes(rows: list[dict]) -> list[ThemeCount]:
        """Sessões distintas por tema normalizado (caixa e espaços); mostra a grafia mais comum."""
        sessions: Counter = Counter()
        spellings: dict[str, Counter] = {}
        for row in rows:
            seen: set[str] = set()
            for synthesis in row.get("sinteses", []):
                if synthesis.get("escopo") != "sessao":
                    continue
                for theme in synthesis.get("temas", []):
                    original = " ".join(str(theme.get("tema", "")).split())
                    key = original.lower()
                    if not key:
                        continue
                    spellings.setdefault(key, Counter())[original] += 1
                    seen.add(key)
            sessions.update(seen)
        ranked = sorted(sessions.items(), key=lambda item: (-item[1], item[0]))[:DASHBOARD_TOP_THEMES]
        return [
            ThemeCount(tema=sorted(spellings[key].items(), key=lambda s: (-s[1], s[0]))[0][0], sessoes=n)
            for key, n in ranked
        ]
