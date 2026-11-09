import pytest

from app.providers.base import ProviderError
from app.repositories.session_repository import SessionRepository
from app.schemas.interview import InterviewState, Turn
from app.schemas.script import InterviewScript, Question
from app.db.seed import CORE_QUESTIONS, generalist_script
from app.services.interview_service import (
    DEFAULT_CLOSING,
    MAX_DECISION_ATTEMPTS,
    InterviewService,
    deepenings_so_far,
    format_full_conversation,
    format_recent_history,
)

pytestmark = pytest.mark.anyio

LAST_INDEX = len(CORE_QUESTIONS) - 1
SCRIPT = generalist_script()


def graph_state(interview_state: InterviewState, last_answer: str = "uma resposta") -> dict:
    return {
        "interview_state": interview_state,
        "script": SCRIPT,
        "last_answer": last_answer,
        "action": "deepen",
        "next_utterance": "",
    }


class TestCoreQuestions:
    def test_has_four_non_empty_questions(self):
        assert len(CORE_QUESTIONS) == 4
        assert all(question.strip() for question in CORE_QUESTIONS)

    def test_start_asks_the_first_question_of_the_seed(self, state):
        assert InterviewService.start(state, SCRIPT) == CORE_QUESTIONS[0]


class TestFormatRecentHistory:
    def test_empty_conversation_returns_placeholder(self):
        assert format_recent_history([]) == "(sem histórico ainda)"

    def test_formats_each_turn_as_role_and_text(self, turns):
        assert format_recent_history(turns("Olá", "Oi")) == "interviewer: Olá\nparticipant: Oi"

    def test_keeps_only_the_last_six_turns(self, turns):
        history = format_recent_history(turns(*[f"t{index}" for index in range(8)]))

        assert len(history.splitlines()) == 6
        assert "t0" not in history
        assert "t1" not in history
        assert history.splitlines()[0].endswith("t2")
        assert history.splitlines()[-1].endswith("t7")

    def test_keeps_everything_when_exactly_six_turns(self, turns):
        history = format_recent_history(turns(*[f"t{index}" for index in range(6)]))

        assert len(history.splitlines()) == 6
        assert "t0" in history


class TestFormatFullConversation:
    def test_empty_conversation_returns_placeholder(self):
        assert format_full_conversation([]) == "(sem histórico ainda)"

    def test_includes_every_turn_without_truncating(self, turns):
        conversation = turns(*[f"t{index}" for index in range(10)])

        formatted = format_full_conversation(conversation)

        assert len(formatted.splitlines()) == 10
        assert "t0" in formatted and "t9" in formatted


class TestConstruction:
    def test_uses_the_injected_llm(self, fake_llm):
        assert InterviewService(llm=fake_llm)._llm is fake_llm

    def test_compiles_the_graph_on_construction(self, service):
        assert service._graph is not None


class TestDecideNode:
    async def test_deepen_keeps_action_and_utterance(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="Por que isso te incomoda?")

        result = await service._decide_node(graph_state(state))

        assert result["action"] == "deepen"
        assert result["next_utterance"] == "Por que isso te incomoda?"

    async def test_preserves_the_untouched_state_keys(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="E depois?")

        result = await service._decide_node(graph_state(state, last_answer="trabalho com suporte"))

        assert result["last_answer"] == "trabalho com suporte"
        assert result["interview_state"] is state

    async def test_merges_profile_updates_into_the_interview_state(self, service, fake_llm, state):
        fake_llm.queue(profile_updates={"cargo": "analista", "sentimento": "frustrado"})

        await service._decide_node(graph_state(state))

        assert state.profile == {"cargo": "analista", "sentimento": "frustrado"}

    async def test_profile_updates_overwrite_existing_keys(self, service, fake_llm, state):
        state.profile = {"cargo": "estagiário", "contexto": "varejo"}
        fake_llm.queue(profile_updates={"cargo": "gerente"})

        await service._decide_node(graph_state(state))

        assert state.profile == {"cargo": "gerente", "contexto": "varejo"}

    async def test_deepen_without_utterance_is_retried_then_falls_back_to_advance(
        self, service, fake_llm, state
    ):
        fake_llm.queue_payload({"action": "deepen"}).queue_payload({"action": "deepen"})

        result = await service._decide_node(graph_state(state))

        assert result["action"] == "advance"
        assert len(fake_llm.prompts) == MAX_DECISION_ATTEMPTS
        assert state.profile == {}

    async def test_tolerates_advance_without_optional_keys(self, service, fake_llm, state):
        fake_llm.queue_payload({"action": "advance"})

        result = await service._decide_node(graph_state(state))

        assert result["next_utterance"] == ""
        assert state.profile == {}

    async def test_finish_before_the_last_question_is_downgraded_to_advance(self, service, fake_llm, state):
        state.current_index = 0
        fake_llm.queue(action="finish", closing_statement="Era só isso, obrigado!")

        result = await service._decide_node(graph_state(state))

        assert result["action"] == "advance"
        assert result["next_utterance"] != "Era só isso, obrigado!"

    async def test_finish_on_the_last_question_uses_the_closing_statement(self, service, fake_llm, state):
        state.current_index = LAST_INDEX
        fake_llm.queue(action="finish", closing_statement="Valeu pelo tempo!")

        result = await service._decide_node(graph_state(state))

        assert result["action"] == "finish"
        assert result["next_utterance"] == "Valeu pelo tempo!"

    async def test_finish_falls_back_to_the_default_closing(self, service, fake_llm, state):
        state.current_index = LAST_INDEX
        fake_llm.queue(action="finish", closing_statement="")

        result = await service._decide_node(graph_state(state))

        assert result["next_utterance"] == DEFAULT_CLOSING

    async def test_prompt_carries_the_current_and_remaining_questions(self, service, fake_llm, state):
        state.current_index = 1
        fake_llm.queue()

        await service._decide_node(graph_state(state, last_answer="uso todo dia"))

        prompt = fake_llm.last_prompt
        assert CORE_QUESTIONS[1] in prompt
        assert CORE_QUESTIONS[2] in prompt
        assert CORE_QUESTIONS[3] in prompt
        assert "uso todo dia" in prompt

    async def test_prompt_says_nenhuma_when_no_question_remains(self, service, fake_llm, state):
        state.current_index = LAST_INDEX
        fake_llm.queue(action="finish")

        await service._decide_node(graph_state(state))

        assert "nenhuma" in fake_llm.last_prompt

    async def test_prompt_carries_the_recent_history(self, service, fake_llm, state):
        state.conversation = [Turn(role="interviewer", text="Como é seu dia?")]
        fake_llm.queue()

        await service._decide_node(graph_state(state))

        assert "interviewer: Como é seu dia?" in fake_llm.last_prompt


class TestCompiledGraph:
    async def test_compiled_graph_runs_the_decide_node(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="Me dá um exemplo?")

        result = await service._graph.ainvoke(graph_state(state))

        assert result["action"] == "deepen"
        assert result["next_utterance"] == "Me dá um exemplo?"


class TestRunTurn:
    async def test_records_the_participant_and_the_interviewer_turns(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="Como assim?")

        await service.run_turn(state, SCRIPT, "é confuso")

        assert [(turn.role, turn.text) for turn in state.conversation] == [
            ("participant", "é confuso"),
            ("interviewer", "Como assim?"),
        ]

    async def test_returns_the_same_state_object_and_the_utterance(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="Como assim?")

        returned_state, utterance = await service.run_turn(state, SCRIPT, "é confuso")

        assert returned_state is state
        assert utterance == "Como assim?"

    async def test_deepen_does_not_advance_the_interview(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="Pode detalhar?")

        await service.run_turn(state, SCRIPT, "mais ou menos")

        assert state.current_index == 0
        assert state.asked_indices == []
        assert state.finished is False

    async def test_advance_moves_to_the_next_question(self, service, fake_llm, state):
        fake_llm.queue(action="advance", next_utterance="Vamos ao próximo ponto.")

        _, utterance = await service.run_turn(state, SCRIPT, "cobri tudo")

        assert state.asked_indices == [0]
        assert state.current_index == 1
        assert state.finished is False
        assert utterance == "Vamos ao próximo ponto."

    async def test_advance_without_utterance_falls_back_to_the_core_question(self, service, fake_llm, state):
        fake_llm.queue(action="advance", next_utterance="")

        _, utterance = await service.run_turn(state, SCRIPT, "cobri tudo")

        assert utterance == CORE_QUESTIONS[1]
        assert state.conversation[-1].text == CORE_QUESTIONS[1]

    async def test_advance_past_the_last_question_finishes_the_interview(self, service, fake_llm, state):
        state.current_index = LAST_INDEX
        fake_llm.queue(action="advance", next_utterance="Próxima pergunta.")

        _, utterance = await service.run_turn(state, SCRIPT, "cobri tudo")

        assert state.finished is True
        assert state.current_index == len(CORE_QUESTIONS)
        assert state.asked_indices == [LAST_INDEX]
        assert utterance == DEFAULT_CLOSING

    async def test_finish_marks_the_state_as_finished(self, service, fake_llm, state):
        state.current_index = LAST_INDEX
        fake_llm.queue(action="finish", closing_statement="Obrigado, foi ótimo!")

        _, utterance = await service.run_turn(state, SCRIPT, "acho que é isso")

        assert state.finished is True
        assert utterance == "Obrigado, foi ótimo!"

    async def test_profile_updates_survive_the_graph_execution(self, service, fake_llm, state):
        fake_llm.queue(
            action="deepen", next_utterance="E o resto?", profile_updates={"cargo": "designer"}
        )

        returned_state, _ = await service.run_turn(state, SCRIPT, "sou designer")

        assert returned_state.profile == {"cargo": "designer"}

    async def test_profile_accumulates_across_turns(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="E daí?", profile_updates={"cargo": "designer"})
        fake_llm.queue(action="deepen", next_utterance="Sério?", profile_updates={"sentimento": "cansado"})

        await service.run_turn(state, SCRIPT, "sou designer")
        await service.run_turn(state, SCRIPT, "ando cansado")

        assert state.profile == {"cargo": "designer", "sentimento": "cansado"}

    async def test_history_sent_to_the_model_grows_with_the_conversation(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="Conta mais.")
        fake_llm.queue(action="deepen", next_utterance="E depois?")

        await service.run_turn(state, SCRIPT, "primeira resposta")
        await service.run_turn(state, SCRIPT, "segunda resposta")

        second_prompt = fake_llm.last_prompt
        assert "participant: primeira resposta" in second_prompt
        assert "interviewer: Conta mais." in second_prompt
        assert "participant: segunda resposta" in second_prompt

    async def test_walks_through_every_core_question_until_finished(self, service, fake_llm, state):
        for _ in CORE_QUESTIONS:
            fake_llm.queue(action="advance", next_utterance="")

        utterances = [(await service.run_turn(state, SCRIPT, "respondi"))[1] for _ in CORE_QUESTIONS]

        assert utterances == [*CORE_QUESTIONS[1:], DEFAULT_CLOSING]
        assert state.asked_indices == list(range(len(CORE_QUESTIONS)))
        assert state.current_index == len(CORE_QUESTIONS)
        assert state.finished is True
        assert len(state.conversation) == 2 * len(CORE_QUESTIONS)


class TestDecisionValidation:
    async def test_invalid_payload_is_retried_once(self, service, fake_llm, state):
        fake_llm.queue_payload({"next_utterance": "sem action"})
        fake_llm.queue(action="deepen", next_utterance="Me conta mais?")
        _, fala = await service.run_turn(state, SCRIPT, "resposta")
        assert fala == "Me conta mais?" and len(fake_llm.prompts) == 2

    async def test_unknown_action_falls_back_to_advance_after_retries(
        self, service, fake_llm, state
    ):
        fake_llm.queue_payload({"action": "skip"}).queue_payload({"action": "skip"})
        _, fala = await service.run_turn(state, SCRIPT, "resposta")
        assert state.current_index == 1 and fala == CORE_QUESTIONS[1]
        assert len(fake_llm.prompts) == MAX_DECISION_ATTEMPTS

    async def test_validation_failure_log_does_not_leak_llm_payload(
        self, service, fake_llm, state, caplog
    ):
        payload = {"action": "Maria Silva", "next_utterance": "Maria Silva mora em SP"}
        fake_llm.queue_payload(payload).queue_payload(payload)
        with caplog.at_level("WARNING"):
            await service.run_turn(state, SCRIPT, "resposta")
        assert "Maria Silva" not in caplog.text
        assert "tentativa 1/" in caplog.text and "ValidationError" in caplog.text

    async def test_provider_error_log_has_cause_type_but_not_message(
        self, service, fake_llm, state, caplog
    ):
        try:
            try:
                raise PermissionError("chave sk-secreta invalida")
            except PermissionError as cause:
                raise ProviderError("Falha: chave sk-secreta invalida") from cause
        except ProviderError as err:
            fake_llm.queue_error(err).queue_error(err)
        with caplog.at_level("WARNING"):
            await service.run_turn(state, SCRIPT, "resposta")
        assert "PermissionError" in caplog.text and "ProviderError" in caplog.text
        assert "sk-secreta" not in caplog.text

    async def test_provider_error_falls_back_to_advance(self, service, fake_llm, state):
        fake_llm.queue_error(ProviderError("timeout")).queue_error(ProviderError("timeout"))
        _, fala = await service.run_turn(state, SCRIPT, "resposta")
        assert fala == CORE_QUESTIONS[1] and not state.finished

    async def test_provider_error_then_success_uses_the_success(self, service, fake_llm, state):
        fake_llm.queue_error(ProviderError("timeout")).queue(
            action="deepen", next_utterance="E aí?"
        )
        _, fala = await service.run_turn(state, SCRIPT, "resposta")
        assert fala == "E aí?" and state.current_index == 0

    async def test_fallback_on_the_last_question_finishes(self, service, fake_llm, state):
        state.current_index = LAST_INDEX
        fake_llm.queue_payload({}).queue_payload({})
        _, fala = await service.run_turn(state, SCRIPT, "resposta")
        assert state.finished and fala == DEFAULT_CLOSING

    async def test_non_string_profile_values_survive_a_repository_round_trip(
        self, service, fake_llm, state, fake_db
    ):
        repo = SessionRepository(fake_db)
        await repo.create(state)
        fake_llm.queue(
            action="deepen",
            next_utterance="?",
            profile_updates={"idade": 42, "turnos": ["manhã"], "x": None},
        )
        await service.run_turn(state, SCRIPT, "resposta")
        await repo.save(state)
        reloaded = await repo.get(state.session_id)
        assert reloaded.profile == {"idade": "42", "turnos": "manhã"}


class TestNoRealApiCalls:
    async def test_unqueued_call_fails_loudly(self, service, state):
        with pytest.raises(AssertionError, match="Chamada inesperada"):
            await service._decide_node(graph_state(state))


# --------------------------------------------------------------------------
# EV-01: o roteiro vem do banco (InterviewScript) e os turnos são anotados
# --------------------------------------------------------------------------


def two_question_script(max_aprofundamentos: int = 1) -> InterviewScript:
    return InterviewScript(
        script_id="transporte",
        titulo="Transporte público",
        perguntas=[
            Question(ordem=10, texto="Como você se desloca?", objetivo="Mapear o trajeto.",
                     max_aprofundamentos=max_aprofundamentos),
            Question(ordem=20, texto="O que mudaria no ônibus?"),
        ],
    )


class TestStart:
    def test_records_the_opening_question_with_its_order(self, service, state):
        script = two_question_script()

        pergunta = service.start(state, script)

        assert pergunta == "Como você se desloca?"
        assert state.script_id == "entrevista-generalista"  # quem liga a sessão é o SessionService
        opening = state.conversation[-1]
        assert (opening.role, opening.text, opening.pergunta_ordem, opening.acao) == (
            "interviewer", "Como você se desloca?", 10, None,
        )


class TestScriptDrivenTurns:
    async def test_uses_the_questions_of_the_given_script(self, service, fake_llm, state):
        fake_llm.queue(action="advance", next_utterance="")

        _, fala = await service.run_turn(state, two_question_script(), "de ônibus")

        assert fala == "O que mudaria no ônibus?"
        assert "Como você se desloca?" in fake_llm.prompts[0]

    async def test_prompt_carries_the_goal_and_numbered_remaining_questions(
        self, service, fake_llm, state
    ):
        fake_llm.queue()

        await service.run_turn(state, two_question_script(), "de ônibus")

        prompt = fake_llm.last_prompt
        assert "Objetivo desta pergunta: Mapear o trajeto." in prompt
        assert "20. O que mudaria no ônibus?" in prompt
        assert "['" not in prompt  # nada de repr de lista no prompt

    async def test_annotates_participant_and_interviewer_turns(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="Quanto tempo leva?")

        await service.run_turn(state, two_question_script(), "de ônibus")

        participant, interviewer = state.conversation[-2:]
        assert (participant.pergunta_ordem, participant.acao) == (10, None)
        assert (interviewer.pergunta_ordem, interviewer.acao) == (10, "deepen")
        assert interviewer.latencia_ms is not None and interviewer.latencia_ms >= 0

    async def test_advance_turn_belongs_to_the_next_question(self, service, fake_llm, state):
        fake_llm.queue(action="advance", next_utterance="")

        await service.run_turn(state, two_question_script(), "de ônibus")

        assert (state.conversation[-1].pergunta_ordem, state.conversation[-1].acao) == (20, "advance")

    async def test_closing_turn_has_no_question(self, service, fake_llm, state):
        state.current_index = 1
        fake_llm.queue(action="advance", next_utterance="")

        await service.run_turn(state, two_question_script(), "nada")

        assert state.finished
        assert (state.conversation[-1].pergunta_ordem, state.conversation[-1].acao) == (None, "advance")

    async def test_finish_closing_has_the_same_shape_as_advance_closing(self, service, fake_llm, state):
        state.current_index = 1
        fake_llm.queue(action="finish", closing_statement="Obrigada!")

        await service.run_turn(state, two_question_script(), "nada")

        closing = state.conversation[-1]
        assert (closing.pergunta_ordem, closing.acao, closing.text) == (None, "finish", "Obrigada!")
        assert state.asked_indices == [1]
        assert state.current_index == 2  # igual ao encerramento por advance

    async def test_deepen_beyond_the_question_limit_becomes_advance(self, service, fake_llm, state):
        script = two_question_script(max_aprofundamentos=1)
        fake_llm.queue(action="deepen", next_utterance="Quanto tempo leva?")
        fake_llm.queue(action="deepen", next_utterance="E no domingo?")

        await service.run_turn(state, script, "de ônibus")
        _, fala = await service.run_turn(state, script, "uma hora")

        assert fala == "O que mudaria no ônibus?"
        assert state.current_index == 1
        assert "E no domingo?" not in [turn.text for turn in state.conversation]

    async def test_zero_deepenings_allowed_always_advances(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="Quanto tempo leva?")

        _, fala = await service.run_turn(state, two_question_script(max_aprofundamentos=0), "a pé")

        assert fala == "O que mudaria no ônibus?"

    async def test_shortened_script_finishes_instead_of_crashing(self, service, fake_llm, state):
        state.current_index = 2  # a sessão estava na 3ª pergunta; o roteiro agora tem 2

        _, fala = await service.run_turn(state, two_question_script(), "resposta")

        assert state.finished and fala == DEFAULT_CLOSING
        assert fake_llm.prompts == []
        assert state.conversation[-2].text == "resposta"


class TestDeepeningsSoFar:
    def test_counts_only_interviewer_deepens_of_the_question(self):
        conversation = [
            Turn(role="interviewer", text="a", acao="deepen", pergunta_ordem=1),
            Turn(role="interviewer", text="b", acao="deepen", pergunta_ordem=2),
            Turn(role="participant", text="c", pergunta_ordem=1),
            Turn(role="interviewer", text="d", acao="advance", pergunta_ordem=1),
            Turn(role="interviewer", text="e", acao="deepen", pergunta_ordem=1),
        ]

        assert deepenings_so_far(conversation, 1) == 2
        assert deepenings_so_far(conversation, 3) == 0
