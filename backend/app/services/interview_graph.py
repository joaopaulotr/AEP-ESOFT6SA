"""Grafo LangGraph da entrevista (EV-40).

START -> safety_check -> (pedido_parar -> encerrar_a_pedido | sofrimento -> acolher | ok -> decide)
decide -> (risco -> acolher/encerrar_a_pedido | deepen -> aprofundar | advance -> transicionar
           | finish -> encerrar)
Todos os nós finais vão para END. Uma chamada ao LLM por turno (nó `decide`).
"""

import logging
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from app.prompts.interview_prompts import DECISION_PROMPT
from app.providers.base import LLMProvider, ProviderError
from app.schemas.decision import DecisionResult
from app.schemas.interview import Action, InterviewState, Turn
from app.schemas.script import InterviewScript, Question
from app.services.safety import check_safety, mentions_stop

logger = logging.getLogger(__name__)

DEFAULT_CLOSING = "Agradeço muito pela conversa. Encerramos por aqui."

STOP_CLOSING = "Tudo bem, vamos parar por aqui. Obrigado por ter conversado comigo."
ACOLHIMENTO = (
    "{nome} aqui. Agradeço por me contar isso. O que você está sentindo importa. "
    "Se estiver passando por um momento difícil, você pode conversar agora com o CVV, "
    "de graça e a qualquer hora, pelo telefone 188 ou pelo site cvv.org.br. "
    "Vou encerrar nossa conversa por aqui para você poder cuidar de si. "
    "Se quiser, a gente conversa outro dia."
)

# Marca do acolhimento no perfil (sem texto da pessoa): é o que diz, depois, que a
# entrevista terminou no acolhimento (TurnResponse.acolhimento e a rota pública).
ALERT_KEY = "alerta"
ALERT_WELCOME = "acolhimento"

HISTORY_WINDOW = 6
LAST_UTTERANCES = 3
SAID_BEFORE_LIMIT = 8
SAID_BEFORE_CHARS = 160

MAX_DECISION_ATTEMPTS = 2  # 1 tentativa + 1 retry
FALLBACK_DECISION = DecisionResult(action="advance")  # decisão documentada no EV-11


def format_recent_history(conversation: list[Turn]) -> str:
    recent = conversation[-HISTORY_WINDOW:]
    return "\n".join(f"{turn.role}: {turn.text}" for turn in recent) or "(sem histórico ainda)"


def _history_for_prompt(conversation: list[Turn]) -> str:
    """Histórico sem a resposta atual (já vai no bloco delimitado) e com a fala da
    pessoa higienizada, para o texto dela não escapar dos delimitadores."""
    past = list(conversation)
    if past and past[-1].role == "participant":
        past = past[:-1]
    recent = past[-HISTORY_WINDOW:]
    lines = [f"{t.role}: {_clean(t.text)}" for t in recent]
    return "\n".join(lines) or "(sem histórico ainda)"


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


def _clean(text: str) -> str:
    """Impede que a fala da pessoa feche o delimitador do prompt."""
    return text.replace("<<<", "").replace(">>>", "")


def _said_before(conversation: list[Turn]) -> str:
    """Falas anteriores do participante (a última, já registrada, é a resposta atual)."""
    spoken = [t.text for t in conversation if t.role == "participant"][:-1]
    recent = spoken[-SAID_BEFORE_LIMIT:]
    return "\n".join(f"- {_clean(t)[:SAID_BEFORE_CHARS]}" for t in recent) or "(nada ainda)"


def _last_utterances(conversation: list[Turn]) -> str:
    said = [_clean(t.text) for t in conversation if t.role == "interviewer"][-LAST_UTTERANCES:]
    return "\n".join(f"- {t}" for t in said) or "(nenhuma ainda)"


def _format_profile(profile: dict[str, str]) -> str:
    return "; ".join(f"{_clean(k)}: {_clean(v)}" for k, v in profile.items()) or "nada ainda"


def _with_acknowledgement(reconhecimento: str, utterance: str) -> str:
    rec = reconhecimento.strip()
    if rec and rec.lower() not in utterance.lower():
        return f"{rec} {utterance}".strip()
    return utterance


class GraphState(TypedDict):
    interview_state: InterviewState
    script: InterviewScript
    last_answer: str
    decision: DecisionResult | None
    risco: Literal["nenhum", "sofrimento", "pedido_parar"]
    acao: Action | None
    pergunta_ordem: int | None
    next_utterance: str


class InterviewGraphBuilder:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    # ---- decisão (LLM) -------------------------------------------------

    async def _request_decision(self, prompt: str) -> DecisionResult | None:
        """Decisão validada, ou None se o LLM falhou nas duas tentativas."""
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
        return None

    @staticmethod
    def _current(state: GraphState) -> Question:
        return state["script"].perguntas[state["interview_state"].current_index]

    def _build_prompt(self, state: GraphState) -> str:
        interview_state = state["interview_state"]
        script = state["script"]
        perguntas = script.perguntas
        current = perguntas[interview_state.current_index]
        remaining = perguntas[interview_state.current_index + 1 :]
        left = max(
            0,
            current.max_aprofundamentos
            - deepenings_so_far(interview_state.conversation, current.ordem),
        )
        return DECISION_PROMPT.format(
            persona_nome=script.persona.nome,
            persona_tom=script.persona.tom,
            current_question=current.texto,
            question_goal=current.objetivo or "não informado",
            deepenings_left=left,
            remaining_questions=format_questions(remaining),
            profile=_format_profile(interview_state.profile),
            said_before=_said_before(interview_state.conversation),
            history=_history_for_prompt(interview_state.conversation),
            last_utterances=_last_utterances(interview_state.conversation),
            last_answer=_clean(state["last_answer"]),
        )

    # ---- nós -----------------------------------------------------------

    async def safety_check(self, state: GraphState) -> dict:
        return {"risco": check_safety(state["last_answer"])}

    async def decide(self, state: GraphState) -> dict:
        decision = await self._request_decision(self._build_prompt(state))
        if decision is None:
            # Sem o LLM, a lista ampla de parada decide: na dúvida, respeitar um possível
            # pedido de parar é melhor que seguir para a próxima pergunta.
            if mentions_stop(state["last_answer"]):
                logger.warning("Tentativas esgotadas; mensagem com frase de parada: encerrando a pedido.")
                return {"decision": FALLBACK_DECISION, "risco": "pedido_parar"}
            logger.warning("Tentativas esgotadas; usando decisão de fallback (advance).")
            return {"decision": FALLBACK_DECISION, "risco": "nenhum"}
        if decision.risco == "nenhum":
            updates = {k: v for k, v in decision.profile_updates.items() if k != ALERT_KEY}
            state["interview_state"].profile.update(updates)
        return {"decision": decision, "risco": decision.risco}

    async def aprofundar(self, state: GraphState) -> dict:
        decision = state["decision"]
        current = self._current(state)
        if (
            deepenings_so_far(state["interview_state"].conversation, current.ordem)
            >= current.max_aprofundamentos
        ):
            # Limite da pergunta atingido: a fala de aprofundamento do LLM é descartada.
            silent = decision.model_copy(update={"next_utterance": ""})
            return await self.transicionar({**state, "decision": silent})
        utterance = _with_acknowledgement(decision.reconhecimento, decision.next_utterance)
        return {"acao": "deepen", "pergunta_ordem": current.ordem, "next_utterance": utterance}

    async def transicionar(self, state: GraphState) -> dict:
        interview_state = state["interview_state"]
        perguntas = state["script"].perguntas
        decision = state["decision"]
        interview_state.asked_indices.append(interview_state.current_index)
        interview_state.current_index += 1
        if interview_state.current_index >= len(perguntas):
            return self._closing(state, "advance")
        proxima = perguntas[interview_state.current_index]
        if decision.next_utterance.strip():
            utterance = _with_acknowledgement(decision.reconhecimento, decision.next_utterance)
        else:
            utterance = f"{decision.reconhecimento.strip() or 'Entendi.'} {proxima.texto}"
        return {"acao": "advance", "pergunta_ordem": proxima.ordem, "next_utterance": utterance}

    async def encerrar(self, state: GraphState) -> dict:
        interview_state = state["interview_state"]
        interview_state.asked_indices.append(interview_state.current_index)
        interview_state.current_index += 1
        return self._closing(state, "finish")

    def _closing(self, state: GraphState, acao: Action) -> dict:
        decision = state["decision"]
        text = decision.closing_statement.strip() or DEFAULT_CLOSING
        state["interview_state"].finished = True
        return {"acao": acao, "pergunta_ordem": None, "next_utterance": text}

    async def encerrar_a_pedido(self, state: GraphState) -> dict:
        state["interview_state"].finished = True
        return {"acao": "finish", "pergunta_ordem": None, "next_utterance": STOP_CLOSING}

    async def acolher(self, state: GraphState) -> dict:
        interview_state = state["interview_state"]
        interview_state.finished = True
        interview_state.profile[ALERT_KEY] = ALERT_WELCOME  # sem texto da pessoa
        text = ACOLHIMENTO.format(nome=state["script"].persona.nome)
        return {"acao": "finish", "pergunta_ordem": None, "next_utterance": text}

    # ---- roteamento ----------------------------------------------------

    @staticmethod
    def route_safety(state: GraphState) -> str:
        return {"pedido_parar": "encerrar_a_pedido", "sofrimento": "acolher"}.get(
            state["risco"], "decide"
        )

    @staticmethod
    def route_decision(state: GraphState) -> str:
        if state["risco"] == "sofrimento":
            return "acolher"
        if state["risco"] == "pedido_parar":
            return "encerrar_a_pedido"
        action = state["decision"].action
        remaining = len(state["script"].perguntas) - state["interview_state"].current_index - 1
        if action == "finish":
            # "finish" antes da última pergunta vira advance (nada se perde).
            return "encerrar" if remaining <= 0 else "transicionar"
        return "aprofundar" if action == "deepen" else "transicionar"

    def build(self):
        graph = StateGraph(GraphState)
        for name in (
            "safety_check",
            "decide",
            "aprofundar",
            "transicionar",
            "encerrar",
            "encerrar_a_pedido",
            "acolher",
        ):
            graph.add_node(name, getattr(self, name))
        graph.add_edge(START, "safety_check")
        graph.add_conditional_edges(
            "safety_check", self.route_safety, ["encerrar_a_pedido", "acolher", "decide"]
        )
        graph.add_conditional_edges(
            "decide",
            self.route_decision,
            ["acolher", "encerrar_a_pedido", "aprofundar", "transicionar", "encerrar"],
        )
        for name in ("aprofundar", "transicionar", "encerrar", "encerrar_a_pedido", "acolher"):
            graph.add_edge(name, END)
        return graph.compile()


def build_interview_graph(llm: LLMProvider):
    return InterviewGraphBuilder(llm).build()


def ended_in_welcome(interview_state: InterviewState) -> bool:
    """A entrevista terminou no acolhimento (o nó `acolher` encerra e marca o perfil)."""
    return interview_state.finished and interview_state.profile.get(ALERT_KEY) == ALERT_WELCOME
