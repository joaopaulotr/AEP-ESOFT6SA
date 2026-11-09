from app.core.errors import ConflictError
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.api import ParticipantCreate, ParticipantUpdate
from app.schemas.participant import Participant

HAS_SESSIONS_MESSAGE = "Este participante tem entrevistas registradas e não pode ser apagado."


class ParticipantService:
    def __init__(self, participants: ParticipantRepository, sessions: SessionRepository) -> None:
        self._participants = participants
        self._sessions = sessions

    async def list(self, *, limit: int = 100) -> list[Participant]:
        return await self._participants.list(limit=limit)

    async def get(self, participant_id: str) -> Participant:
        return await self._participants.get_or_raise(participant_id)

    async def create(self, data: ParticipantCreate) -> Participant:
        return await self._participants.create(Participant(**data.model_dump()))

    async def update(self, participant_id: str, data: ParticipantUpdate) -> Participant:
        """Sem `versao` de propósito: baixa concorrência e todos os campos opcionais; vale a última escrita."""
        participant = await self._participants.get_or_raise(participant_id)
        changes = data.model_dump(exclude_unset=True)
        if changes.get("canal") is None:
            changes.pop("canal", None)
        for field, value in changes.items():
            setattr(participant, field, value)
        if not await self._participants.save(participant):
            await self._participants.get_or_raise(participant_id)  # apagado no meio -> 404
        return participant

    async def delete(self, participant_id: str) -> None:
        await self._participants.get_or_raise(participant_id)
        if await self._sessions.has_for_participant(participant_id):
            raise ConflictError(HAS_SESSIONS_MESSAGE)  # não apaga histórico
        await self._participants.delete(participant_id)
