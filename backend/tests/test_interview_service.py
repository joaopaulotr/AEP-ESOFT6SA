import pytest

from app.schemas.interview import InterviewState, Turn
from app.services.interview_service import (
    CORE_QUESTIONS,
    DEFAULT_CLOSING,
    InterviewService,
    format_full_conversation,
    format_recent_history,
)

LAST_INDEX = len(CORE_QUESTIONS) - 1


def graph_state(interview_state: InterviewState, last_answer: str = "uma resposta") -> dict:
    return {
        "interview_state": interview_state,
        "last_answer": last_answer,
        "action": "deepen",
        "next_utterance": "",
    }


class TestCoreQuestions:
    def test_has_four_non_empty_questions(self):
        assert len(CORE_QUESTIONS) == 4
        assert all(question.strip() for question in CORE_QUESTIONS)

    def test_opening_question_returns_the_first_one(self):
        assert InterviewService.opening_question() == CORE_QUESTIONS[0]


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
    def test_uses_the_injected_llm_client(self, fake_llm):
        assert InterviewService(llm_client=fake_llm)._llm is fake_llm

    def test_compiles_the_graph_on_construction(self, service):
        assert service._graph is not None


class TestDecideNode:
    def test_deepen_keeps_action_and_utterance(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="Por que isso te incomoda?")

        result = service._decide_node(graph_state(state))

        assert result["action"] == "deepen"
        assert result["next_utterance"] == "Por que isso te incomoda?"

    def test_preserves_the_untouched_state_keys(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="E depois?")

        result = service._decide_node(graph_state(state, last_answer="trabalho com suporte"))

        assert result["last_answer"] == "trabalho com suporte"
        assert result["interview_state"] is state

    def test_merges_profile_updates_into_the_interview_state(self, service, fake_llm, state):
        fake_llm.queue(profile_updates={"cargo": "analista", "sentimento": "frustrado"})

        service._decide_node(graph_state(state))

        assert state.profile == {"cargo": "analista", "sentimento": "frustrado"}

    def test_profile_updates_overwrite_existing_keys(self, service, fake_llm, state):
        state.profile = {"cargo": "estagiário", "contexto": "varejo"}
        fake_llm.queue(profile_updates={"cargo": "gerente"})

        service._decide_node(graph_state(state))

        assert state.profile == {"cargo": "gerente", "contexto": "varejo"}

    def test_tolerates_response_without_optional_keys(self, service, fake_llm, state):
        fake_llm.queue_payload({"action": "deepen"})

        result = service._decide_node(graph_state(state))

        assert result["next_utterance"] == ""
        assert state.profile == {}

    def test_finish_before_the_last_question_is_downgraded_to_advance(self, service, fake_llm, state):
        state.current_index = 0
        fake_llm.queue(action="finish", closing_statement="Era só isso, obrigado!")

        result = service._decide_node(graph_state(state))

        assert result["action"] == "advance"
        assert result["next_utterance"] != "Era só isso, obrigado!"

    def test_finish_on_the_last_question_uses_the_closing_statement(self, service, fake_llm, state):
        state.current_index = LAST_INDEX
        fake_llm.queue(action="finish", closing_statement="Valeu pelo tempo!")

        result = service._decide_node(graph_state(state))

        assert result["action"] == "finish"
        assert result["next_utterance"] == "Valeu pelo tempo!"

    def test_finish_falls_back_to_the_default_closing(self, service, fake_llm, state):
        state.current_index = LAST_INDEX
        fake_llm.queue(action="finish", closing_statement="")

        result = service._decide_node(graph_state(state))

        assert result["next_utterance"] == DEFAULT_CLOSING

    def test_prompt_carries_the_current_and_remaining_questions(self, service, fake_llm, state):
        state.current_index = 1
        fake_llm.queue()

        service._decide_node(graph_state(state, last_answer="uso todo dia"))

        prompt = fake_llm.last_prompt
        assert CORE_QUESTIONS[1] in prompt
        assert CORE_QUESTIONS[2] in prompt
        assert CORE_QUESTIONS[3] in prompt
        assert "uso todo dia" in prompt

    def test_prompt_says_nenhuma_when_no_question_remains(self, service, fake_llm, state):
        state.current_index = LAST_INDEX
        fake_llm.queue(action="finish")

        service._decide_node(graph_state(state))

        assert "nenhuma" in fake_llm.last_prompt

    def test_prompt_carries_the_recent_history(self, service, fake_llm, state):
        state.conversation = [Turn(role="interviewer", text="Como é seu dia?")]
        fake_llm.queue()

        service._decide_node(graph_state(state))

        assert "interviewer: Como é seu dia?" in fake_llm.last_prompt


class TestCompiledGraph:
    def test_compiled_graph_runs_the_decide_node(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="Me dá um exemplo?")

        result = service._graph.invoke(graph_state(state))

        assert result["action"] == "deepen"
        assert result["next_utterance"] == "Me dá um exemplo?"


class TestRunTurn:
    def test_records_the_participant_and_the_interviewer_turns(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="Como assim?")

        service.run_turn(state, "é confuso")

        assert [(turn.role, turn.text) for turn in state.conversation] == [
            ("participant", "é confuso"),
            ("interviewer", "Como assim?"),
        ]

    def test_returns_the_same_state_object_and_the_utterance(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="Como assim?")

        returned_state, utterance = service.run_turn(state, "é confuso")

        assert returned_state is state
        assert utterance == "Como assim?"

    def test_deepen_does_not_advance_the_interview(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="Pode detalhar?")

        service.run_turn(state, "mais ou menos")

        assert state.current_index == 0
        assert state.asked_indices == []
        assert state.finished is False

    def test_advance_moves_to_the_next_question(self, service, fake_llm, state):
        fake_llm.queue(action="advance", next_utterance="Vamos ao próximo ponto.")

        _, utterance = service.run_turn(state, "cobri tudo")

        assert state.asked_indices == [0]
        assert state.current_index == 1
        assert state.finished is False
        assert utterance == "Vamos ao próximo ponto."

    def test_advance_without_utterance_falls_back_to_the_core_question(self, service, fake_llm, state):
        fake_llm.queue(action="advance", next_utterance="")

        _, utterance = service.run_turn(state, "cobri tudo")

        assert utterance == CORE_QUESTIONS[1]
        assert state.conversation[-1].text == CORE_QUESTIONS[1]

    def test_advance_past_the_last_question_finishes_the_interview(self, service, fake_llm, state):
        state.current_index = LAST_INDEX
        fake_llm.queue(action="advance", next_utterance="Próxima pergunta.")

        _, utterance = service.run_turn(state, "cobri tudo")

        assert state.finished is True
        assert state.current_index == len(CORE_QUESTIONS)
        assert state.asked_indices == [LAST_INDEX]
        assert utterance == DEFAULT_CLOSING

    def test_finish_marks_the_state_as_finished(self, service, fake_llm, state):
        state.current_index = LAST_INDEX
        fake_llm.queue(action="finish", closing_statement="Obrigado, foi ótimo!")

        _, utterance = service.run_turn(state, "acho que é isso")

        assert state.finished is True
        assert state.current_index == LAST_INDEX
        assert state.asked_indices == []
        assert utterance == "Obrigado, foi ótimo!"

    def test_profile_updates_survive_the_graph_execution(self, service, fake_llm, state):
        fake_llm.queue(
            action="deepen", next_utterance="E o resto?", profile_updates={"cargo": "designer"}
        )

        returned_state, _ = service.run_turn(state, "sou designer")

        assert returned_state.profile == {"cargo": "designer"}

    def test_profile_accumulates_across_turns(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="E daí?", profile_updates={"cargo": "designer"})
        fake_llm.queue(action="deepen", next_utterance="Sério?", profile_updates={"sentimento": "cansado"})

        service.run_turn(state, "sou designer")
        service.run_turn(state, "ando cansado")

        assert state.profile == {"cargo": "designer", "sentimento": "cansado"}

    def test_history_sent_to_the_model_grows_with_the_conversation(self, service, fake_llm, state):
        fake_llm.queue(action="deepen", next_utterance="Conta mais.")
        fake_llm.queue(action="deepen", next_utterance="E depois?")

        service.run_turn(state, "primeira resposta")
        service.run_turn(state, "segunda resposta")

        second_prompt = fake_llm.last_prompt
        assert "participant: primeira resposta" in second_prompt
        assert "interviewer: Conta mais." in second_prompt
        assert "participant: segunda resposta" in second_prompt

    def test_walks_through_every_core_question_until_finished(self, service, fake_llm, state):
        for _ in CORE_QUESTIONS:
            fake_llm.queue(action="advance", next_utterance="")

        utterances = [service.run_turn(state, "respondi")[1] for _ in CORE_QUESTIONS]

        assert utterances == [*CORE_QUESTIONS[1:], DEFAULT_CLOSING]
        assert state.asked_indices == list(range(len(CORE_QUESTIONS)))
        assert state.current_index == len(CORE_QUESTIONS)
        assert state.finished is True
        assert len(state.conversation) == 2 * len(CORE_QUESTIONS)


class TestNoRealApiCalls:
    def test_unqueued_call_fails_loudly(self, service, state):
        with pytest.raises(AssertionError, match="Chamada inesperada"):
            service._decide_node(graph_state(state))

    def test_default_construction_never_reaches_the_network(self):
        with pytest.raises(AssertionError, match="cliente OpenAI real"):
            InterviewService()
