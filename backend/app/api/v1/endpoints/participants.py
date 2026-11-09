from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_participant_service
from app.schemas.api import ParticipantCreate, ParticipantUpdate
from app.schemas.participant import Participant
from app.services.participant_service import ParticipantService

router = APIRouter(prefix="/participants")


@router.get("", response_model=list[Participant])
async def list_participants(participants: ParticipantService = Depends(get_participant_service)):
    return await participants.list()


@router.post("", response_model=Participant, status_code=status.HTTP_201_CREATED)
async def create_participant(
    payload: ParticipantCreate, participants: ParticipantService = Depends(get_participant_service)
):
    return await participants.create(payload)


@router.get("/{participant_id}", response_model=Participant)
async def get_participant(
    participant_id: str, participants: ParticipantService = Depends(get_participant_service)
):
    return await participants.get(participant_id)


@router.put("/{participant_id}", response_model=Participant)
async def update_participant(
    participant_id: str,
    payload: ParticipantUpdate,
    participants: ParticipantService = Depends(get_participant_service),
):
    return await participants.update(participant_id, payload)


@router.delete("/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_participant(
    participant_id: str, participants: ParticipantService = Depends(get_participant_service)
):
    await participants.delete(participant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
