import logging
import time
from typing import Literal, TypedDict

from pydantic import ValidationError
from langgraph.graph import END, START, StateGraph

from app.prompts.interview_prompts import DECISION_PROMPT
from app.providers.base import LLMProvider, ProviderError
from app.schemas.decision import DecisionResult
from app.schemas.interview import InterviewState, Turn
from app.schemas.script import InterviewScript, Question

logger = logging.getLogger(__name__)

DEFAULT_CLOSING = "Obrigado pela sua participação, encerramos por aqui."

HISTORY_WINDOW = 6

MAX_DECISION_ATTEMPTS = 2  # 1 tentativa + 1 retry
FALLBACK_DECISION = DecisionResult(action="advance")


def format_recent_history(conversation: list[Turn]) -> str:
    recent = conversation[-HISTORY_WINDOW:]
    return "\n".join(f"{turn.role}: {turn.text}" for turn in recent) or "(sem histórico ainda)"


def format_full_conversation(conversation: list[Turn]) -> str:
    return "\n".join(f"{turn.role}: {turn.text}" for turn in conversation) or "(sem histórico ainda)"


def format_questions(questions: list[Question]) -> str:
    return "\n".join(f"{q.ordem}. {q.texto}" for q in questions) or "nenhuma"


def deepenings_so_far(conversation: list[Turn], ordem: int) -> int:
    """Quantos aprofundamentos o entrevistador já fez na pergunta `ordem`."""
    return sum(
        1
        for turn in conversation
        if turn.role == "interviewer" and turn.acao == "deepen" and turn.pergunta_ordem == ordem
    )


class GraphState(TypedDict):
    interview_state: InterviewState
    script: InterviewScript
    last_answer: str
    action: Literal["deepen", "advance", "finish"]
    next_utterance: str


class InterviewService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm
        self._graph = self._build_graph()

    @staticmethod
    def opening_question(script: InterviewScript) -> str:
        return script.perguntas[0].texto

    def start(self, interview_state: InterviewState, script: InterviewScript) -> str:
        """Registra a pergunta de abertura do roteiro na conversa."""
        pergunta = script.perguntas[0]
        interview_state.script_id = script.script_id
        interview_state.conversation.append(
            Turn(role="interviewer", text=pergunta.texto, pergunta_ordem=pergunta.ordem)
        )
        return pergunta.texto

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
                # Nunca logar str(exc) nem o payload: ValidationError inclui a entrada
                # bruta do LLM, que pode conter dados pessoais do participante.
                details = (
                    [(e["loc"], e["type"]) for e in exc.errors(include_input=False)]
                    if isinstance(exc, ValidationError)
                    else None
                )
                # Só o tipo da causa (ex.: AuthenticationError), nunca a mensagem.
                cause = type(exc.__cause__).__name__ if exc.__cause__ else ""
                logger.warning(
                    "Decisão do LLM inválida (tentativa %d/%d): %s %s %s",
                    attempt,
                    MAX_DECISION_ATTEMPTS,
                    type(exc).__name__,
                    details or "",
                    f"causa={cause}" if cause else "",
                )
        logger.warning("Tentativas esgotadas; usando decisão de fallback (advance).")
        return FALLBACK_DECISION

    async def _decide_node(self, state: GraphState) -> GraphState:
        interview_state = state["interview_state"]
        perguntas = state["script"].perguntas
        current = perguntas[interview_state.current_index]
        remaining = perguntas[interview_state.current_index + 1 :]

        prompt = DECISION_PROMPT.format(
            current_question=current.texto,
            question_goal=current.objetivo or "não informado",
            remaining_questions=format_questions(remaining),
            history=format_recent_history(interview_state.conversation),
            last_answer=state["last_answer"],
        )
        decision = await self._request_decision(prompt)

        interview_state.profile.update(decision.profile_updates)

        action = decision.action
        if action == "finish" and remaining:
            action = "advance"
        if action == "deepen" and (
            deepenings_so_far(interview_state.conversation, current.ordem)
            >= current.max_aprofundamentos
        ):
            action = "advance"  # limite de aprofundamentos da pergunta atingido

        next_utterance = decision.next_utterance if action == decision.action else ""
        if action == "finish":
            next_utterance = decision.closing_statement or DEFAULT_CLOSING

        return {**state, "action": action, "next_utterance": next_utterance}

    async def run_turn(
        self, interview_state: InterviewState, script: InterviewScript, participant_text: str
    ) -> tuple[InterviewState, str]:
        perguntas = script.perguntas
        if interview_state.current_index >= len(perguntas):
            # O roteiro foi encurtado depois que a sessão começou: encerra com a
            # resposta registrada em vez de quebrar a entrevista.
            interview_state.conversation.append(Turn(role="participant", text=participant_text))
            self.finish(interview_state)
            return interview_state, DEFAULT_CLOSING

        ordem_atual = perguntas[interview_state.current_index].ordem
        interview_state.conversation.append(
            Turn(role="participant", text=participant_text, pergunta_ordem=ordem_atual)
        )

        started = time.perf_counter()
        result = await self._graph.ainvoke(
            {
                "interview_state": interview_state,
                "script": script,
                "last_answer": participant_text,
                "action": "deepen",
                "next_utterance": "",
            }
        )
        latencia_ms = int((time.perf_counter() - started) * 1000)

        action = result["action"]
        next_utterance = result["next_utterance"]
        pergunta_ordem: int | None = ordem_atual

        if action == "advance":
            interview_state.asked_indices.append(interview_state.current_index)
            interview_state.current_index += 1
            if interview_state.current_index >= len(perguntas):
                interview_state.finished = True
                next_utterance = DEFAULT_CLOSING
                pergunta_ordem = None
            else:
                proxima = perguntas[interview_state.current_index]
                next_utterance = next_utterance or proxima.texto
                pergunta_ordem = proxima.ordem
        elif action == "finish":
            interview_state.finished = True

        interview_state.conversation.append(
            Turn(
                role="interviewer",
                text=next_utterance,
                pergunta_ordem=pergunta_ordem,
                acao=action,
                latencia_ms=latencia_ms,
            )
        )

        return interview_state, next_utterance
