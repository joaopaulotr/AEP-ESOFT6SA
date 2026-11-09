"""Roteiro inicial gravado no banco no startup (EV-01).

As perguntas são as mesmas da v0.1.0, que antes eram uma constante no
InterviewService. Agora elas são um documento de interview_scripts.
"""

from app.schemas.script import DEFAULT_SCRIPT_ID, InterviewScript, Persona, Question

CORE_QUESTIONS = [
    "Para começar, me conta um pouco sobre você e sobre o seu dia a dia.",
    "Como o tema desta conversa aparece na sua rotina? Me conta como foi a última vez.",
    "O que mais te incomoda ou te atrapalha nesse contexto hoje?",
    "Se você pudesse mudar uma coisa, o que seria — e por quê?",
]

_OBJECTIVES = [
    "Conhecer quem é a pessoa e o contexto em que ela vive.",
    "Ouvir uma situação concreta e recente ligada ao tema.",
    "Identificar dificuldades e barreiras.",
    "Levantar mudanças desejadas e o motivo delas.",
]


def generalist_script() -> InterviewScript:
    """Roteiro 'Entrevista generalista' (seed)."""
    return InterviewScript(
        script_id=DEFAULT_SCRIPT_ID,
        titulo="Entrevista generalista",
        tema="Dia a dia e dificuldades",
        descricao="Roteiro padrão com as quatro perguntas centrais da primeira versão.",
        perguntas=[
            Question(ordem=index, texto=texto, objetivo=objetivo)
            for index, (texto, objetivo) in enumerate(zip(CORE_QUESTIONS, _OBJECTIVES), start=1)
        ],
        persona=Persona(nome="Ana", tom="acolhedor"),
        slug_convite="generalista",
    )
