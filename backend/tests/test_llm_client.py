import json

import pytest

from app.services.llm_client import LLMClient


class TestCompleteJson:
    def test_parses_the_json_payload(self, fake_openai):
        fake_openai.queue_json({"action": "advance", "next_utterance": "Vamos lá."})

        result = LLMClient(client=fake_openai).complete_json("um prompt")

        assert result == {"action": "advance", "next_utterance": "Vamos lá."}

    def test_asks_the_model_for_a_json_object(self, fake_openai):
        fake_openai.queue_json({"action": "deepen"})

        LLMClient(client=fake_openai).complete_json("um prompt")

        call = fake_openai.last_call
        assert call["response_format"] == {"type": "json_object"}
        assert call["model"] == "gpt-4o-mini"
        assert call["messages"] == [{"role": "user", "content": "um prompt"}]

    def test_propagates_invalid_json(self, fake_openai):
        fake_openai.queue_raw("isto não é json")

        with pytest.raises(json.JSONDecodeError):
            LLMClient(client=fake_openai).complete_json("um prompt")


class TestCompleteText:
    def test_returns_the_raw_content(self, fake_openai):
        fake_openai.queue_raw("uma síntese qualquer")

        assert LLMClient(client=fake_openai).complete_text("um prompt") == "uma síntese qualquer"

    def test_does_not_force_a_response_format(self, fake_openai):
        fake_openai.queue_raw("texto")

        LLMClient(client=fake_openai).complete_text("um prompt")

        assert "response_format" not in fake_openai.last_call
        assert fake_openai.last_call["messages"] == [{"role": "user", "content": "um prompt"}]


class TestModelSelection:
    def test_defaults_to_gpt_4o_mini(self, fake_openai):
        fake_openai.queue_raw("texto")

        LLMClient(client=fake_openai).complete_text("um prompt")

        assert fake_openai.last_call["model"] == "gpt-4o-mini"

    def test_honours_a_custom_model(self, fake_openai):
        fake_openai.queue_raw("texto")

        LLMClient(client=fake_openai, model="gpt-4o").complete_text("um prompt")

        assert fake_openai.last_call["model"] == "gpt-4o"


class TestNoRealApiCalls:
    def test_default_construction_never_reaches_the_network(self):
        with pytest.raises(AssertionError, match="cliente OpenAI real"):
            LLMClient()
