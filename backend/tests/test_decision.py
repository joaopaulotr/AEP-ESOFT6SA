import pytest
from pydantic import ValidationError

from app.schemas.decision import DecisionResult


def test_parses_a_complete_payload():
    d = DecisionResult.model_validate({"action": "deepen", "next_utterance": "Por quê?",
                                       "profile_updates": {"cargo": "motorista"}, "closing_statement": ""})
    assert d.action == "deepen" and d.profile_updates == {"cargo": "motorista"}


def test_optional_fields_default_to_empty():
    d = DecisionResult.model_validate({"action": "advance"})
    assert (d.next_utterance, d.profile_updates, d.closing_statement) == ("", {}, "")


def test_missing_action_is_invalid():
    with pytest.raises(ValidationError):
        DecisionResult.model_validate({"next_utterance": "x"})


def test_unknown_action_is_invalid():
    with pytest.raises(ValidationError):
        DecisionResult.model_validate({"action": "skip"})


def test_null_strings_become_empty():
    d = DecisionResult.model_validate({"action": "finish", "next_utterance": None, "closing_statement": None})
    assert d.next_utterance == "" and d.closing_statement == ""


def test_profile_values_are_coerced_to_strings():
    d = DecisionResult.model_validate({"action": "advance", "profile_updates": {
        "idade": 42, "ativo": True, "turnos": ["manhã", "noite"], "nada": None, "obj": {"a": 1}}})
    assert d.profile_updates == {"idade": "42", "ativo": "true", "turnos": "manhã, noite"}


def test_profile_float_becomes_string():
    d = DecisionResult.model_validate({"action": "advance", "profile_updates": {"nota": 3.5}})
    assert d.profile_updates == {"nota": "3.5"}


def test_profile_list_skips_non_scalars_and_empty_list_is_dropped():
    d = DecisionResult.model_validate({"action": "advance", "profile_updates": {
        "mix": ["a", None, {"x": 1}, 2], "vazio": []}})
    assert d.profile_updates == {"mix": "a, 2"}


def test_profile_updates_null_becomes_empty():
    assert DecisionResult.model_validate({"action": "advance", "profile_updates": None}).profile_updates == {}


def test_extra_keys_are_ignored():
    assert DecisionResult.model_validate({"action": "advance", "foo": 1}).action == "advance"


@pytest.mark.parametrize("utterance", [None, "", "   "])
def test_deepen_requires_a_non_blank_utterance(utterance):
    with pytest.raises(ValidationError):
        DecisionResult.model_validate({"action": "deepen", "next_utterance": utterance})


def test_advance_and_finish_do_not_require_an_utterance():
    assert DecisionResult.model_validate({"action": "advance"}).action == "advance"
    assert DecisionResult.model_validate({"action": "finish"}).action == "finish"


def test_blank_profile_values_are_dropped():
    d = DecisionResult.model_validate(
        {"action": "advance", "profile_updates": {"cargo": "", "setor": "  ", "lista": [" "], "nome": "Ana"}}
    )
    assert d.profile_updates == {"nome": "Ana"}


def test_list_profile_values_are_joined():
    d = DecisionResult.model_validate({"action": "advance", "profile_updates": {"tags": ["a", 2]}})
    assert d.profile_updates == {"tags": "a, 2"}
