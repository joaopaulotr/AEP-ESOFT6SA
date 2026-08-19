from app.services.session_service import get_session
from openai import OpenAI
from app.services.interview_service import _format_full_conversation
from app.prompts.synthesis_prompts import SYNTESIS_PROMPT

client = OpenAI()


async def create_synthesis_session(id_session: str) -> str:
    interview_state = await get_session(id_session)
    if interview_state is None:
        raise ValueError("Session not found.")
    if not interview_state.finished:
        raise ValueError("Cannot create synthesis before finishing the interview.")

    prompt = SYNTESIS_PROMPT.format(
        conversation=_format_full_conversation(interview_state.conversation),
        profile=interview_state.profile,
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
