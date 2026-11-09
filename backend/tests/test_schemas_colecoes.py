"""Modelos das quatro coleções (EV-01)."""

import pytest
from pydantic import ValidationError

from app.db.seed import CORE_QUESTIONS, generalist_script
from app.schemas.interview import InterviewState, Turn
from app.schemas.participant import Participant
from app.schemas.script import DEFAULT_SCRIPT_ID, InterviewScript, Question, slugify
from app.schemas.synthesis import Citation, Synthesis, Theme


def _script(**overrides) -> InterviewScript:
    data = {"titulo": "Transporte Público", "perguntas": [Question(ordem=1, texto="Como vai?")]}
    return InterviewScript(**{**data, **overrides})


class TestSlugify:
    @pytest.mark.parametrize(
        ("texto", "esperado"),
        [
            ("Transporte Público 2026", "transporte-publico-2026"),
            ("  Saúde & Bem-estar!  ", "saude-bem-estar"),
            ("***", ""),
        ],
    )
    def test_normalizes_to_url_safe_ascii(self, texto, esperado):
        assert slugify(texto) == esperado


class TestQuestion:
    def test_strips_the_text(self):
        assert Question(ordem=1, texto="  Como vai?  ").texto == "Como vai?"

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"ordem": 0, "texto": "x"},
            {"ordem": 1, "texto": ""},
            {"ordem": 1, "texto": "   "},
            {"ordem": 1, "texto": "x", "max_aprofundamentos": 6},
            {"ordem": 1, "texto": "x", "max_aprofundamentos": -1},
        ],
    )
    def test_rejects_invalid_values(self, kwargs):
        with pytest.raises(ValidationError):
            Question(**kwargs)

    def test_defaults_to_two_deepenings(self):
        assert Question(ordem=1, texto="x").max_aprofundamentos == 2


class TestInterviewScript:
    def test_requires_at_least_one_question(self):
        with pytest.raises(ValidationError):
            _script(perguntas=[])

    def test_sorts_the_questions_by_order(self):
        script = _script(
            perguntas=[Question(ordem=3, texto="c"), Question(ordem=1, texto="a")]
        )

        assert [q.texto for q in script.perguntas] == ["a", "c"]

    def test_rejects_repeated_orders(self):
        with pytest.raises(ValidationError, match="mesma ordem"):
            _script(perguntas=[Question(ordem=1, texto="a"), Question(ordem=1, texto="b")])

    def test_generates_the_invite_slug_from_the_title(self):
        script = _script(script_id="abcdef123456")

        assert script.slug_convite == "transporte-publico-abcdef12"

    def test_title_without_letters_still_gets_a_slug(self):
        assert _script(titulo="???", script_id="12345678x").slug_convite == "roteiro-12345678"

    def test_normalizes_a_given_slug(self):
        assert _script(slug_convite="Meu Convite").slug_convite == "meu-convite"

    def test_has_nested_origin_and_persona(self):
        document = _script().model_dump()

        assert document["origem"] == {"tipo": "manual", "arquivo": None, "extraido_em": None}
        assert document["persona"] == {"nome": "Ana", "tom": "acolhedor"}
        assert document["perguntas"][0]["max_aprofundamentos"] == 2

    def test_rejects_unknown_persona_tone(self):
        with pytest.raises(ValidationError):
            _script(persona={"nome": "Bia", "tom": "sarcastico"})


class TestSeedScript:
    def test_turns_the_v1_questions_into_a_script(self):
        seed = generalist_script()

        assert seed.script_id == DEFAULT_SCRIPT_ID
        assert seed.slug_convite == "generalista"
        assert [q.texto for q in seed.perguntas] == CORE_QUESTIONS
        assert [q.ordem for q in seed.perguntas] == [1, 2, 3, 4]
        assert all(q.objetivo for q in seed.perguntas)


class TestParticipant:
    def test_identification_is_optional(self):
        participant = Participant()

        assert participant.participant_id
        assert (participant.apelido, participant.faixa_etaria, participant.regiao) == (None, None, None)
        assert participant.canal == "voz"

    def test_rejects_unknown_channel(self):
        with pytest.raises(ValidationError):
            Participant(canal="telefone")


class TestSynthesis:
    def test_session_scope_requires_a_session(self):
        with pytest.raises(ValidationError, match="exige session_id"):
            Synthesis(escopo="sessao", script_id="s", resumo="r")

    def test_script_scope_rejects_a_session(self):
        with pytest.raises(ValidationError, match="não pertence a uma sessão"):
            Synthesis(escopo="roteiro", script_id="s", session_id="x", resumo="r")

    def test_holds_themes_with_citations(self):
        synthesis = Synthesis(
            escopo="roteiro",
            script_id="s",
            resumo="r",
            temas=[Theme(tema="atraso", pontos=["ônibus"], citacoes=[Citation(texto="sempre atrasa", session_id="a")])],
        )

        assert synthesis.model_dump()["temas"][0]["citacoes"][0] == {
            "texto": "sempre atrasa",
            "session_id": "a",
        }


class TestInterviewState:
    def test_references_the_seed_script_by_default(self):
        assert InterviewState().script_id == DEFAULT_SCRIPT_ID

    def test_status_follows_finished_and_is_stored(self):
        state = InterviewState()
        assert state.model_dump()["status"] == "em_andamento"

        state.finished = True
        assert state.model_dump()["status"] == "concluida"

    def test_stored_status_is_ignored_when_loading(self):
        state = InterviewState.model_validate({"finished": False, "status": "concluida"})

        assert state.status == "em_andamento"

    def test_loads_a_v010_document(self):
        """Documento gravado pela 1ª entrega: sem script_id, com synthesis e asked_indices."""
        legacy = {
            "session_id": "antiga",
            "asked_indices": [0],
            "current_index": 1,
            "conversation": [
                {"role": "interviewer", "text": "Oi", "timestamp": "2026-09-10T22:10:00Z"},
            ],
            "profile": {"cargo": "agente"},
            "finished": False,
            "synthesis": None,
            "created_at": "2026-09-10T22:10:00Z",
            "updated_at": "2026-09-10T22:10:00Z",
        }

        state = InterviewState.model_validate(legacy)

        assert state.script_id == DEFAULT_SCRIPT_ID
        assert state.participant_id is None
        assert state.metricas.tokens == 0
        assert state.conversation[0].acao is None

    def test_turn_rejects_negative_latency_and_unknown_action(self):
        with pytest.raises(ValidationError):
            Turn(role="interviewer", text="x", latencia_ms=-1)
        with pytest.raises(ValidationError):
            Turn(role="interviewer", text="x", acao="skip")
