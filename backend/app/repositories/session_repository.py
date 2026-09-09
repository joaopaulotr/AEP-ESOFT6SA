from datetime import datetime, timezone

from app.db.mongodb import db as default_db
from app.schemas.interview import InterviewState


class SessionRepository:
    def __init__(self, database=None, collection: str = "interview_sessions") -> None:
        self._db = database if database is not None else default_db
        self._collection = collection

    @property
    def _sessions(self):
        return self._db[self._collection]

    async def create(self, state: InterviewState) -> InterviewState:
        await self._sessions.insert_one(state.model_dump())
        return state

    async def get(self, session_id: str) -> InterviewState | None:
        document = await self._sessions.find_one({"session_id": session_id})
        if document is None:
            return None
        document.pop("_id", None)
        return InterviewState(**document)

    async def save(self, state: InterviewState) -> None:
        state.updated_at = datetime.now(timezone.utc)
        await self._sessions.update_one(
            {"session_id": state.session_id},
            {"$set": state.model_dump()},
        )

    async def delete(self, session_id: str) -> None:
        result = await self._sessions.delete_one({"session_id": session_id})
        if result.deleted_count == 0:
            raise ValueError("Sessão não encontrada.")

    async def list_all(self) -> list[InterviewState]:
        documents = await self._sessions.find().to_list(length=None)
        for document in documents:
            document.pop("_id", None)
        return [InterviewState(**document) for document in documents]
