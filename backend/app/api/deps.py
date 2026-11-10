from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.db import mongodb
from app.importing.questionnaire_parser import QuestionnaireParser
from app.providers.base import LLMProvider, SpeechProvider
from app.providers.factory import build_llm_provider, build_speech_provider
from app.repositories.base import BaseRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.script_repository import ScriptRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.synthesis_repository import SynthesisRepository
from app.services.invite_service import InviteService
from app.services.import_service import ImportService
from app.services.interview_service import InterviewService
from app.services.participant_service import ParticipantService
from app.services.script_service import ScriptService
from app.services.session_service import SessionService
from app.services.synthesis_service import SynthesisService


@lru_cache(maxsize=1)
def get_database() -> Any:
    return mongodb.db


@lru_cache(maxsize=1)
def get_script_repository() -> ScriptRepository:
    return ScriptRepository(get_database())


@lru_cache(maxsize=1)
def get_participant_repository() -> ParticipantRepository:
    return ParticipantRepository(get_database())


@lru_cache(maxsize=1)
def get_session_repository() -> SessionRepository:
    return SessionRepository(get_database())


@lru_cache(maxsize=1)
def get_synthesis_repository() -> SynthesisRepository:
    return SynthesisRepository(get_database())


def get_repositories() -> tuple[BaseRepository, ...]:
    """Todos os repositórios, para criar índices no startup."""
    return (
        get_script_repository(),
        get_participant_repository(),
        get_session_repository(),
        get_synthesis_repository(),
    )


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    return build_llm_provider(settings)


@lru_cache(maxsize=1)
def get_speech_provider() -> SpeechProvider:
    return build_speech_provider(settings)


@lru_cache(maxsize=1)
def get_interview_service() -> InterviewService:
    return InterviewService(llm=get_llm_provider())


@lru_cache(maxsize=1)
def get_session_service() -> SessionService:
    return SessionService(
        sessions=get_session_repository(),
        scripts=get_script_repository(),
        participants=get_participant_repository(),
        interview=get_interview_service(),
        syntheses=get_synthesis_repository(),
    )


@lru_cache(maxsize=1)
def get_script_service() -> ScriptService:
    return ScriptService(get_script_repository(), get_session_repository())


@lru_cache(maxsize=1)
def get_participant_service() -> ParticipantService:
    return ParticipantService(get_participant_repository(), get_session_repository())


@lru_cache(maxsize=1)
def get_synthesis_service() -> SynthesisService:
    return SynthesisService(
        get_session_repository(), get_synthesis_repository(), get_llm_provider()
    )


@lru_cache(maxsize=1)
def get_import_service() -> ImportService:
    return ImportService(QuestionnaireParser(get_llm_provider()))


@lru_cache(maxsize=1)
def get_invite_service() -> InviteService:
    return InviteService(
        get_script_repository(), get_participant_repository(), get_session_service()
    )


def reset_dependencies() -> None:
    """Limpa os singletons (uso em testes)."""
    for getter in (
        get_database,
        get_script_repository,
        get_participant_repository,
        get_session_repository,
        get_synthesis_repository,
        get_llm_provider,
        get_speech_provider,
        get_interview_service,
        get_session_service,
        get_script_service,
        get_participant_service,
        get_synthesis_service,
        get_import_service,
        get_invite_service,
    ):
        getter.cache_clear()
