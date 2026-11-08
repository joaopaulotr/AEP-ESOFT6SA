import logging
from typing import Literal, TypedDict

from pydantic import ValidationError
from langgraph.graph import END, START, StateGraph

from app.prompts.interview_prompts import DECISION_PROMPT
from app.providers.base import LLMProvider, ProviderError
from app.schemas.decision import DecisionResult
from app.schemas.interview import InterviewState, Turn

logger = logging.getLogger(__name__)

CORE_QUESTIONS = [
    "Para começar, me conta um pouco sobre você e sobre o seu dia a dia.",
    "Como o tema desta conversa aparece na sua rotina? Me conta como foi a última vez.",
    "O que mais te incomoda ou te atrapalha nesse contexto hoje?",
    "Se você pudesse mudar uma coisa, o que seria — e por quê?",
]

DEFAULT_CLOSING = "Obrigado pela sua participação, encerramos por aqui."

HISTORY_WINDOW = 6

MAX_DECISION_ATTEMPTS = 2  # 1 tentativa + 1 retry
FALLBACK_DECISION = DecisionResult(action="advance")


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
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm
        self._graph = self._build_graph()

    @staticmethod
    def opening_question() -> str:
        return CORE_QUESTIONS[0]

    def finish(self, interview_state: InterviewState) -> InterviewState:
        if not interview_state.finished:
            interview_state.finished = True
            interview_state.conversation.append(Turn(role="interviewer", text=DEFAULT_CLOSING))
        return interview_state

    def _build_graph(self):
        graph = StateGraph(GraphState)
        graph.add_node("decide", self._decide_node)
        graph.add_edge(START, "decide")
        graph.add_edge("decide", END)
        return graph.compile()

    async def _request_decision(self, prompt: str) -> DecisionResult:
        for attempt in range(1, MAX_DECISION_ATTEMPTS + 1):
            try:
                return DecisionResult.model_validate(await self._llm.complete_json(prompt))
            except (ProviderError, ValidationError) as exc:
                logger.warning(
                    "Decisão do LLM inválida (tentativa %d/%d): %s",
                    attempt,
                    MAX_DECISION_ATTEMPTS,
                    exc,
                )
        logger.warning("Tentativas esgotadas; usando decisão de fallback (advance).")
        return FALLBACK_DECISION

    async def _decide_node(self, state: GraphState) -> GraphState:
        interview_state = state["interview_state"]
        current_question = CORE_QUESTIONS[interview_state.current_index]
        remaining = CORE_QUESTIONS[interview_state.current_index + 1 :]

        prompt = DECISION_PROMPT.format(
            current_question=current_question,
            remaining_questions=remaining or "nenhuma",
            history=format_recent_history(interview_state.conversation),
            last_answer=state["last_answer"],
        )
        decision = await self._request_decision(prompt)

        interview_state.profile.update(decision.profile_updates)

        action = decision.action
        if action == "finish" and interview_state.current_index < len(CORE_QUESTIONS) - 1:
            action = "advance"

        next_utterance = decision.next_utterance
        if action == "finish":
            next_utterance = decision.closing_statement or DEFAULT_CLOSING

        return {**state, "action": action, "next_utterance": next_utterance}

    async def run_turn(
        self, interview_state: InterviewState, participant_text: str
    ) -> tuple[InterviewState, str]:
        interview_state.conversation.append(Turn(role="participant", text=participant_text))

        result = await self._graph.ainvoke(
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
