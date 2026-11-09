from app.db import collections
from app.repositories.base import BaseRepository
from app.schemas.participant import Participant


class ParticipantRepository(BaseRepository[Participant]):
    model = Participant
    collection_name = collections.PARTICIPANTS
    id_field = "participant_id"
    not_found_message = "Participante não encontrado."
    duplicate_message = "Participante já cadastrado."
