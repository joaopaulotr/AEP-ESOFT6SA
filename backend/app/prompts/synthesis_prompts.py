SYNTESIS_PROMPT = """Você é um pesquisador analisando a transcrição de uma entrevista qualitativa.

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
