from pymongo import ASCENDING, DESCENDING, IndexModel

from app.db import collections
from app.repositories.base import BaseRepository
from app.schemas.script import DEFAULT_SCRIPT_ID
from app.schemas.synthesis import Synthesis


class SynthesisRepository(BaseRepository[Synthesis]):
    model = Synthesis
    collection_name = collections.SYNTHESES
    id_field = "synthesis_id"
    not_found_message = "Síntese não encontrada."
    duplicate_message = "Síntese já existe."
    extra_indexes = (
        IndexModel([("session_id", ASCENDING)], name="session_id"),
        IndexModel([("script_id", ASCENDING), ("escopo", ASCENDING)], name="script_id_escopo"),
    )

    async def get_for_session(self, session_id: str) -> Synthesis | None:
        document = await self._collection.find_one({"escopo": "sessao", "session_id": session_id})
        return None if document is None else self._to_model(document)

    async def delete_for_session(self, session_id: str) -> int:
        """Apaga a síntese da sessão (cascata da exclusão da sessão). Devolve quantas apagou."""
        result = await self._collection.delete_many({"escopo": "sessao", "session_id": session_id})
        return result.deleted_count

    async def list_for_script(self, script_id: str, *, limit: int = 100) -> list[Synthesis]:
        return await self.list({"script_id": script_id}, limit=limit)

    @staticmethod
    def script_synthesis_id(script_id: str) -> str:
        """Id fixo do relatório cruzado de um roteiro (um por roteiro)."""
        return f"roteiro:{script_id}"

    async def get_for_script(self, script_id: str) -> Synthesis | None:
        return await self.get(self.script_synthesis_id(script_id))

    async def list_session_syntheses(self, script_id: str, *, limit: int = 30) -> list[Synthesis]:
        """Sínteses de sessão do roteiro, as mais recentemente atualizadas primeiro."""
        cursor = (
            self._collection.find({"escopo": "sessao", "script_id": script_id})
            .sort([("updated_at", DESCENDING), (self.id_field, ASCENDING)])
            .limit(limit)
        )
        return [self._to_model(document) for document in await cursor.to_list(length=limit)]

    async def save_for_script(self, synthesis: Synthesis) -> Synthesis:
        """Upsert atômico do relatório do roteiro (id fixo; preserva created_at ao regerar)."""
        if synthesis.escopo != "roteiro":
            raise ValueError("save_for_script só aceita síntese de roteiro.")
        synthesis_id = self.script_synthesis_id(synthesis.script_id)
        document = self._to_document(synthesis)
        created_at = document.pop("created_at")
        document.pop("synthesis_id")
        await self._collection.update_one(
            {self.id_field: synthesis_id},
            {"$set": document, "$setOnInsert": {self.id_field: synthesis_id, "created_at": created_at}},
            upsert=True,
        )
        return await self.get_or_raise(synthesis_id)

    async def pull_citations_of_session(self, session_id: str) -> int:
        """Tira as citações da sessão de todos os relatórios de roteiro (cascata da exclusão).
        Devolve quantos relatórios foram alterados."""
        return await self._atomic_pull_citations(session_id)

    async def _atomic_pull_citations(self, session_id: str) -> int:
        """`$pull` atômico em todos os temas de todos os relatórios de roteiro (uma operação
        no servidor, sem ler-e-gravar). O mongomock dos testes ignora `$[]`; lá o conftest
        troca este método por um equivalente em Python."""
        result = await self._collection.update_many(
            {"escopo": "roteiro"},
            {"$pull": {"temas.$[].citacoes": {"session_id": session_id}}},
        )
        return result.modified_count

    @staticmethod
    def session_synthesis_id(session_id: str) -> str:
        """Id fixo da síntese de uma sessão: o índice único de synthesis_id
        garante uma síntese por sessão mesmo com pedidos simultâneos."""
        return f"sessao:{session_id}"

    async def import_legacy(self, session_id: str, resumo: str) -> None:
        """Guarda a síntese que a v0.1.0 deixava dentro da sessão (sem sobrescrever)."""
        synthesis_id = self.session_synthesis_id(session_id)
        legacy = Synthesis(
            synthesis_id=synthesis_id,
            escopo="sessao",
            session_id=session_id,
            script_id=DEFAULT_SCRIPT_ID,
            resumo=resumo,
            modelo="v0.1.0",
        )
        await self._collection.update_one(
            {self.id_field: synthesis_id},
            {"$setOnInsert": self._to_document(legacy)},
            upsert=True,
        )

    async def save_for_session(self, synthesis: Synthesis) -> Synthesis:
        """Upsert atômico: cria na primeira vez; regerar substitui o conteúdo
        e preserva synthesis_id e created_at."""
        if synthesis.escopo != "sessao" or not synthesis.session_id:
            raise ValueError("save_for_session só aceita síntese de sessão.")
        synthesis_id = self.session_synthesis_id(synthesis.session_id)
        document = self._to_document(synthesis)
        created_at = document.pop("created_at")
        document.pop("synthesis_id")
        await self._collection.update_one(
            {self.id_field: synthesis_id},
            {"$set": document, "$setOnInsert": {self.id_field: synthesis_id, "created_at": created_at}},
            upsert=True,
        )
        return await self.get_or_raise(synthesis_id)
