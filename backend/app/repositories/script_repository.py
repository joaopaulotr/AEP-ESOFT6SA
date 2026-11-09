from pymongo import ASCENDING, IndexModel

from app.db.seed import generalist_script
from app.repositories.base import BaseRepository
from app.schemas.script import DEFAULT_SCRIPT_ID, InterviewScript


class ScriptRepository(BaseRepository[InterviewScript]):
    model = InterviewScript
    collection_name = "interview_scripts"
    id_field = "script_id"
    not_found_message = "Roteiro não encontrado."
    duplicate_message = "Já existe um roteiro com esse identificador ou link de convite."
    extra_indexes = (
        IndexModel([("slug_convite", ASCENDING)], unique=True, name="slug_convite_unico"),
        IndexModel([("ativo", ASCENDING)], name="ativo"),
    )

    async def get_by_slug(self, slug: str) -> InterviewScript | None:
        document = await self._collection.find_one({"slug_convite": slug})
        return None if document is None else self._to_model(document)

    async def list_active(self, *, limit: int = 100) -> list[InterviewScript]:
        return await self.list({"ativo": True}, limit=limit)

    async def ensure_seed(self) -> InterviewScript:
        """Grava o roteiro generalista se ele ainda não existir (idempotente).

        Não sobrescreve edições feitas depois no roteiro já gravado.
        """
        seed = generalist_script()
        await self._collection.update_one(
            {self.id_field: seed.script_id},
            {"$setOnInsert": self._to_document(seed)},
            upsert=True,
        )
        return await self.get_or_raise(seed.script_id)

    async def get_default(self) -> InterviewScript:
        """Roteiro usado quando a sessão é aberta sem escolher um."""
        return await self.get(DEFAULT_SCRIPT_ID) or await self.ensure_seed()
