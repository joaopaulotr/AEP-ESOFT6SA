import time

from app.schemas.interview import InterviewState, Turn
from app.schemas.script import InterviewScript
from app.providers.base import LLMProvider
from app.services.interview_graph import (  # noqa: F401  (reexportados para quem já importava daqui)
    DEFAULT_CLOSING,
    FALLBACK_DECISION,
    HISTORY_WINDOW,
    MAX_DECISION_ATTEMPTS,
    build_interview_graph,
    deepenings_so_far,
    format_full_conversation,
    format_questions,
    format_recent_history,
)


class InterviewService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm
        self._graph = build_interview_graph(llm)

    @staticmethod
    def start(interview_state: InterviewState, script: InterviewScript) -> str:
        """Registra a pergunta de abertura do roteiro na conversa e a devolve."""
        pergunta = script.perguntas[0]
        interview_state.conversation.append(
            Turn(role="interviewer", text=pergunta.texto, pergunta_ordem=pergunta.ordem)
        )
        return pergunta.texto

    def finish(self, interview_state: InterviewState) -> InterviewState:
        if not interview_state.finished:
            interview_state.finished = True
            interview_state.conversation.append(Turn(role="interviewer", text=DEFAULT_CLOSING))
        return interview_state

    def close_with_answer(
        self, interview_state: InterviewState, participant_text: str
    ) -> tuple[InterviewState, str]:
        """Registra a última resposta e encerra, quando o roteiro não permite seguir
        (pergunta atual removida ou roteiro apagado). Nada do que a pessoa disse se perde."""
        interview_state.conversation.append(Turn(role="participant", text=participant_text))
        self.finish(interview_state)
        return interview_state, DEFAULT_CLOSING

    async def run_turn(
        self, interview_state: InterviewState, script: InterviewScript, participant_text: str
    ) -> tuple[InterviewState, str]:
        perguntas = script.perguntas
        if interview_state.current_index >= len(perguntas):
            # O roteiro foi encurtado depois que a sessão começou.
            return self.close_with_answer(interview_state, participant_text)

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
                "decision": None,
                "risco": "nenhum",
                "acao": None,
                "pergunta_ordem": ordem_atual,
                "next_utterance": "",
            }
        )
        latencia_ms = int((time.perf_counter() - started) * 1000)

        next_utterance = result["next_utterance"]
        interview_state.conversation.append(
            Turn(
                role="interviewer",
                text=next_utterance,
                pergunta_ordem=result["pergunta_ordem"],
                acao=result["acao"],
                latencia_ms=latencia_ms,
            )
        )
        return interview_state, next_utterance
