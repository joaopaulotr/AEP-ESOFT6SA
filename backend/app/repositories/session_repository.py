from collections.abc import Awaitable, Callable

from pymongo import ASCENDING, DESCENDING, IndexModel

from app.db import collections
from app.repositories.base import BaseRepository
from app.schemas.api import SessionSummary
from app.schemas.interview import (
    ActionCount,
    InterviewState,
    QuestionDeepening,
    ScriptStats,
    SessionDetails,
)
from app.schemas.participant import Participant
from app.schemas.script import DEFAULT_SCRIPT_ID, InterviewScript

LegacySynthesisHandler = Callable[[str, str], Awaitable[None]]  # (session_id, texto)


class SessionRepository(BaseRepository[InterviewState]):
    model = InterviewState
    collection_name = collections.SESSIONS
    id_field = "session_id"
    not_found_message = "Sessão não encontrada."
    duplicate_message = "Sessão já existe."
    stale_message = "A sessão foi alterada por outra ação. Tente de novo."
    extra_indexes = (
        IndexModel([("script_id", ASCENDING), ("created_at", DESCENDING)], name="script_id_data"),
        IndexModel([("participant_id", ASCENDING)], name="participant_id"),
    )

    async def list_by_script(self, script_id: str, *, limit: int = 100) -> list[InterviewState]:
        return await self.list({"script_id": script_id}, limit=limit)

    async def count_by_script(self) -> dict[str, tuple[int, int]]:
        """script_id -> (total, concluídas), numa só agregação."""
        rows = await self._collection.aggregate(
            [
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
