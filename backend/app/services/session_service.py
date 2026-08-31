from app.db.mongodb import db
from app.schemas.interview import InterviewState

COLLECTION = "interview_sessions"

async def create_session(state: InterviewState) -> InterviewState:
    await db[COLLECTION].insert_one(state.model_dump())
    return state

async def get_session(session_id: str) -> InterviewState | None:
    session = await db[COLLECTION].find_one({"session_id": session_id})
    if session:
        session.pop("_id", None)
        return InterviewState(**session)
    return None

async def delete_session(session_id: str) -> None:
    if not await db[COLLECTION].find_one({"session_id": session_id}):
        raise ValueError("Sessão não encontrada.")
    await db[COLLECTION].delete_one({"session_id": session_id})
    return None

async def list_sessions() -> list[InterviewState]:
    sessions = await db[COLLECTION].find().to_list(length=None)
    return [InterviewState(**{k: v for k, v in session.items() if k != "_id"}) for session in sessions]

async def save_session(state: InterviewState) -> None:
    await db[COLLECTION].update_one({"session_id": state.session_id}, {"$set": state.model_dump()})

