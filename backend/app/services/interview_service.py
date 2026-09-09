from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.prompts.interview_prompts import DECISION_PROMPT
from app.schemas.interview import InterviewState, Turn
from app.services.llm_client import LLMClient

CORE_QUESTIONS = [
    "Me conta um pouco sobre como é o seu dia a dia de trabalho.",
    "Qual foi a última vez que você usou um produto ou serviço parecido com este? Como foi?",
    "O que mais te frustra nesse tipo de tarefa hoje?",
    "Se você pudesse mudar uma coisa nesse processo, o que seria?",
]

DEFAULT_CLOSING = "Obrigado pela sua participação, encerramos por aqui."

HISTORY_WINDOW = 6


def format_recent_history(conversation: list[Turn]) -> str:
    recent = conversation[-HISTORY_WINDOW:]
    return "\n".join(f"{turn.role}: {turn.text}" for turn in recent) or "(sem histórico ainda)"


def format_full_conversation(conversation: list[Turn]) -> str:
    return "\n".join(f"{turn.role}: {turn.text}" for turn in conversation) or "(sem histórico ainda)"


class GraphState(TypedDict):
    interview_state: InterviewState
    last_answer: str
    action: Literal["deepen", "advance", "finish"]
    next_utterance: str


class InterviewService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client or LLMClient()
        self._graph = self._build_graph()

    @staticmethod
    def opening_question() -> str:
        return CORE_QUESTIONS[0]

    def _build_graph(self):
        graph = StateGraph(GraphState)
        graph.add_node("decide", self._decide_node)
        graph.add_edge(START, "decide")
        graph.add_edge("decide", END)
        return graph.compile()

    def _decide_node(self, state: GraphState) -> GraphState:
        interview_state = state["interview_state"]
        current_question = CORE_QUESTIONS[interview_state.current_index]
        remaining = CORE_QUESTIONS[interview_state.current_index + 1 :]

        prompt = DECISION_PROMPT.format(
            current_question=current_question,
            remaining_questions=remaining or "nenhuma",
            history=format_recent_history(interview_state.conversation),
            last_answer=state["last_answer"],
        )
        result = self._llm.complete_json(prompt)

        interview_state.profile.update(result.get("profile_updates", {}))

        action = result["action"]
        if action == "finish" and interview_state.current_index < len(CORE_QUESTIONS) - 1:
            action = "advance"

        next_utterance = result.get("next_utterance", "")
        if action == "finish":
            next_utterance = result.get("closing_statement") or DEFAULT_CLOSING

        return {**state, "action": action, "next_utterance": next_utterance}

    def run_turn(
        self, interview_state: InterviewState, participant_text: str
    ) -> tuple[InterviewState, str]:
        interview_state.conversation.append(Turn(role="participant", text=participant_text))

        result = self._graph.invoke(
            {
                "interview_state": interview_state,
                "last_answer": participant_text,
                "action": "deepen",
                "next_utterance": "",
            }
        )

        action = result["action"]
        next_utterance = result["next_utterance"]

        if action == "advance":
            interview_state.asked_indices.append(interview_state.current_index)
            interview_state.current_index += 1
            if interview_state.current_index >= len(CORE_QUESTIONS):
                interview_state.finished = True
                next_utterance = DEFAULT_CLOSING
            else:
                next_utterance = next_utterance or CORE_QUESTIONS[interview_state.current_index]
        elif action == "finish":
            interview_state.finished = True

        interview_state.conversation.append(Turn(role="interviewer", text=next_utterance))

        return interview_state, next_utterance
