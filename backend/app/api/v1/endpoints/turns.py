from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
import io

from app.services.session_service import get_session, save_session
from app.services.interview_service import run_interview_turn
from app.services.voice_service import transcribe_audio, text_to_speech

router = APIRouter()


@router.post("/turn/{session_id}")
async def handle_turn(session_id: str, audio: UploadFile):
    ...
