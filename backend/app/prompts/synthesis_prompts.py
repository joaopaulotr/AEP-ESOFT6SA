SYNTHESIS_PROMPT = """Você é um pesquisador analisando a transcrição de uma entrevista qualitativa.

Perfil extraído do participante:
{profile}

Transcrição completa (entrevistador e participante):
{conversation}

Responda SOMENTE com um objeto JSON neste formato:
{{
  "resumo": "2-3 frases sobre quem é o participante e o contexto",
  "temas": [
    {{"tema": "nome curto do tema", "pontos": ["ponto principal"], "citacoes": ["trecho literal"]}}
  ],
  "lacunas": ["ponto que mereceria aprofundamento numa próxima entrevista"]
}}

Regras:
- Em português, objetivo e sem floreios.
- Cada citação deve ser um trecho literal, copiado palavra por palavra, de uma fala do PARTICIPANTE
  (nunca do entrevistador). Não parafraseie, não corrija e não invente: citação que não for literal será descartada.
- Não invente informação que não esteja na transcrição."""

SYNTHESIS_FALLBACK_PROMPT = """Você é um pesquisador analisando a transcrição de uma entrevista qualitativa.

Perfil extraído do participante:
{profile}

Transcrição completa (entrevistador e participante):
{conversation}

Escreva um relatório de síntese em português, objetivo e sem floreios, com estas seções:

1. Resumo geral (2-3 frases sobre quem é o participante e o contexto).
2. Principais pontos por tema abordado (um parágrafo curto por pergunta central coberta).
3. Insights e sinais relevantes (frustrações, necessidades, contradições, citações marcantes do participante).
4. Lacunas ou pontos que mereceriam aprofundamento numa próxima entrevista.

Não invente informação que não esteja na transcrição."""

SCRIPT_SYNTHESIS_PROMPT = """Você é um pesquisador cruzando as sínteses de várias entrevistas de um mesmo roteiro.

Sínteses individuais (JSON, cada uma com o session_id da entrevista, resumo, temas, pontos e citações):
{syntheses}

Responda SOMENTE com um objeto JSON neste formato:
{{
  "resumo": "visão geral dos padrões entre as entrevistas",
  "temas": [
    {{"tema": "nome curto", "pontos": ["padrão observado"],
      "citacoes": [{{"texto": "citação copiada", "session_id": "id da entrevista de origem"}}]}}
  ],
  "divergencias": ["onde os participantes discordam ou se contradizem"],
  "lacunas": ["o que as entrevistas não cobriram"]
}}

Regras:
- Em português, objetivo e sem floreios.
- Use apenas citações presentes nas sínteses acima, copiadas literalmente, cada uma com o session_id exato de onde veio.
  Citação que não existir na entrada será descartada.
- Não invente informação que não esteja nas sínteses."""
