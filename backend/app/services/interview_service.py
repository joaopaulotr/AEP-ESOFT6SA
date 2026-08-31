import json
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from openai import OpenAI

from app.core.config import settings
from app.prompts.interview_prompts import DECISION_PROMPT
from app.schemas.interview import InterviewState, Turn

CORE_QUESTIONS = [
    "Me conta um pouco sobre como é o seu dia a dia de trabalho.",
    "Qual foi a última vez que você usou um produto ou serviço parecido com este? Como foi?",
    "O que mais te frustra nesse tipo de tarefa hoje?",
    "Se você pudesse mudar uma coisa nesse processo, o que seria?",
]

client = OpenAI(api_key=settings.openai_api_key)


class GraphState(TypedDict):
    interview_state: InterviewState
    last_answer: str
    action: Literal["deepen", "advance", "finish"]
    next_utterance: str


def _format_history(conversation: list[Turn]) -> str:
    recent = conversation[-6:]
    return "\n".join(f"{turn.role}: {turn.text}" for turn in recent) or "(sem histórico ainda)"

def _format_full_conversation(conversation):
    return "\n".join(f"{t.role}: {t.text}" for t in conversation) or "(sem histórico ainda)"



def decide_node(state: GraphState) -> GraphState:
    interview_state = state["interview_state"]
    current_question = CORE_QUESTIONS[interview_state.current_index]
    remaining = CORE_QUESTIONS[interview_state.current_index + 1 :]

    prompt = DECISION_PROMPT.format(
        current_question=current_question,
        remaining_questions=remaining or "nenhuma",
        history=_format_history(interview_state.conversation),
        last_answer=state["last_answer"],
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)

    interview_state.profile.update(result.get("profile_updates", {}))

    action = result["action"]
    if action == "finish" and interview_state.current_index < len(CORE_QUESTIONS) - 1:
        action = "advance"

    next_utterance = result.get("next_utterance", "")
    if action == "finish":
        next_utterance = result.get("closing_statement") or "Obrigado pela sua participação, encerramos por aqui."

    return {**state, "action": action, "next_utterance": next_utterance}


def build_interview_graph():
    graph = StateGraph(GraphState)
    graph.add_node("decide", decide_node)
    graph.add_edge(START, "decide")
    graph.add_edge("decide", END)
    return graph.compile()


_interview_graph = build_interview_graph()


def run_interview_turn(interview_state: InterviewState, participant_text: str) -> tuple[InterviewState, str]:
    interview_state.conversation.append(Turn(role="participant", text=participant_text))

    result = _interview_graph.invoke({
        "interview_state": interview_state,
        "last_answer": participant_text,
        "action": "deepen",
        "next_utterance": "",
    })

    action = result["action"]
    next_utterance = result["next_utterance"]

    if action == "advance":
        interview_state.asked_indices.append(interview_state.current_index)
        interview_state.current_index += 1
        if interview_state.current_index >= len(CORE_QUESTIONS):
            interview_state.finished = True
            next_utterance = "Obrigado pela sua participação, encerramos por aqui."
        else:
            next_utterance = next_utterance or CORE_QUESTIONS[interview_state.current_index]
    elif action == "finish":
        interview_state.finished = True

    interview_state.conversation.append(Turn(role="interviewer", text=next_utterance))

    return interview_state, next_utterance


def get_opening_question() -> str:
    return CORE_QUESTIONS[0]
