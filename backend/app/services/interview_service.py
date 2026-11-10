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
    ended_in_welcome,
    deepenings_so_far,
    format_full_conversation,
    format_questions,
    format_recent_history,
)

OPENING = (
    "Oi, aqui é {nome}. Vou te fazer algumas perguntas, uma de cada vez — "
    "não existe resposta certa ou errada. Leva uns {minutos} minutos."
)
MIN_OPENING_MINUTES = 5
MINUTES_PER_QUESTION = 2


class InterviewService:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm
        self._graph = build_interview_graph(llm)

    @staticmethod
    def opening(script: InterviewScript) -> str:
        """Abertura humana (EV-21): apresentação da persona, combinado e duração, sem gênero."""
        minutos = max(MIN_OPENING_MINUTES, len(script.perguntas) * MINUTES_PER_QUESTION)
        return OPENING.format(nome=script.persona.nome, minutos=minutos)

    @classmethod
    def start(cls, interview_state: InterviewState, script: InterviewScript) -> str:
        """Registra a abertura + a 1ª pergunta do roteiro na conversa e devolve a fala."""
        pergunta = script.perguntas[0]
        fala = f"{cls.opening(script)} {pergunta.texto}"
        interview_state.conversation.append(
            Turn(role="interviewer", text=fala, pergunta_ordem=pergunta.ordem)
        )
        return fala

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
