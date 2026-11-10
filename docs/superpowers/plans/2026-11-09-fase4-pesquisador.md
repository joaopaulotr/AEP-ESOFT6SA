# Fase 4 — Visão do pesquisador: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** O pesquisador vê, por roteiro, um painel com os números da pesquisa (conclusão, duração, aprofundamentos, ações, custo, temas) e um relatório cruzado de todas as entrevistas com citações literais que levam à entrevista de origem; o custo real de cada entrevista é medido.

**Architecture:** Backend mede uso (tokens, segundos de áudio, caracteres de TTS) via um medidor por requisição (`contextvars`) alimentado pelos providers e grava em `interview_sessions.metricas`; logs estruturados em JSON sem conteúdo. A síntese individual vira estruturada (JSON validado, citações conferidas contra a fala real). A síntese de roteiro é map-reduce sobre as sínteses individuais. O painel é uma rota de agregação MongoDB (`$match/$group/$unwind/$lookup/$facet`). Frontend ganha a tela do painel com gráficos SVG próprios e o relatório cruzado.

**Tech Stack:** FastAPI, Motor (aggregation pipelines), Pydantic v2, `contextvars`, `logging` com formatter JSON próprio; React 18, SVG.

**Spec:** `docs/EVOLUCOES.md` — EV-32, EV-33 (inclui a pendência "excluir sessão deve remover suas citações das sínteses de roteiro"), EV-62.

## Global Constraints

- Rotas sob `/api/v1`; `bash scripts/verify-delivery.sh` → `[OK]`; testes sem OpenAI; sem dependências novas (backend e front).
- **Nunca** logar fala, perfil, transcrição ou citação; logs só com ids, nomes de etapa, durações, contagens, tipos de erro.
- Preços para estimar custo ficam em `Settings` (USD): `price_llm_input_per_1m=0.15`, `price_llm_output_per_1m=0.60`, `price_stt_per_minute=0.006`, `price_tts_per_1m_chars=15.0` (valores de referência do gpt-4o-mini / whisper-1 / tts; documentar que são estimativas configuráveis).
- Citação só entra na síntese se o texto for **trecho literal** (após normalizar espaços) de uma fala do participante da sessão citada; senão é descartada.
- Painel e síntese cruzada são do pesquisador (sem auth ainda — RK-11).
- Front: HTTP só via `api.js`; gráficos acessíveis (cada gráfico com título, `role="img"` + `aria-label` com o resumo, e a tabela de dados disponível em "Ver dados"); cores dos tokens (claro/escuro); mobile.

## Review Focus

1. Síntese cruzada com menos de 2 entrevistas com síntese → 409 com orientação; nunca chama o LLM nesse caso.
2. LLM inventa citação (não literal) → descartada; síntese continua válida.
3. Excluir sessão remove as citações dela de todas as sínteses de roteiro (pendência do EV-33).
4. Painel de roteiro sem nenhuma sessão → números zerados e listas vazias, não 500 nem divisão por zero.
5. Medidor de uso não vaza entre requisições simultâneas (contextvar por requisição/tarefa).

---

### Task 1: Backend — métricas de uso e logs estruturados (EV-62)

**Files:** Create `app/core/usage.py` (`UsageMeter`, contextvar, `track_usage()` context manager, `estimate_cost(meter, settings)`), `app/core/logging.py` (`JsonFormatter`, `configure_logging()`), tests `tests/test_usage.py`, `tests/test_logging.py`. Modify `app/providers/openai_provider.py` (reporta `usage.prompt_tokens/completion_tokens` do chat; segundos de áudio pela transcrição — pedir `response_format="verbose_json"` e usar `duration`; caracteres de TTS), `app/providers/fake.py` (reporta números fixos pequenos), `app/services/session_service.py` / `synthesis_service.py` (envolvem a operação com `track_usage()` e somam em `session.metricas`), `app/api/v1/endpoints/voice.py` (transcrição/TTS de uma sessão: aceitar `session_id` opcional em query para atribuir o uso), `app/main.py` (configura logging; middleware de log por requisição: método, rota, status, duração ms, `session_id` se houver no path).

**Interfaces:** `UsageMeter{llm_input_tokens, llm_output_tokens, stt_seconds, tts_chars}` com `add_*`; `current_meter() -> UsageMeter | None`; `SessionMetrics` ganha `llm_input_tokens`, `llm_output_tokens`, `stt_seconds`, `tts_chars` (mantém `tokens`, `segundos_audio`, `custo_usd` coerentes: `tokens = in+out`, `segundos_audio = stt_seconds`, `custo_usd = estimate_cost`). Atualização das métricas usa `$inc` atômico (não read-modify-write) para não brigar com o versionamento.

- [ ] Steps: testes (RED) — medidor isolado entre duas tarefas concorrentes; provider OpenAI reporta usage do dublê; turno soma métricas na sessão; custo estimado com os preços; formatter JSON sem campos de conteúdo; middleware loga status/duração. Implementar. Verify backend. Commit `feat(EV-62): metricas de uso, custo por entrevista e logs estruturados`.

---

### Task 2: Backend — síntese estruturada e cruzada (EV-33)

**Files:** Modify `app/prompts/synthesis_prompts.py`, `app/services/synthesis_service.py`, `app/repositories/synthesis_repository.py` (`pull_citations_of_session(session_id)`), `app/services/session_service.py` (cascata chama o pull), `app/api/v1/endpoints/scripts.py`, `app/schemas/api.py`. Create `app/services/citation_check.py`, tests `tests/test_synthesis_structured.py`, `tests/test_script_synthesis.py`.

**Interfaces:**
- Síntese de sessão: prompt pede JSON `{resumo, temas:[{tema, pontos:[str], citacoes:[str]}], lacunas:[str]}`; validação Pydantic; `filter_literal_citations(citacoes, participant_texts)`; salva `Synthesis` com `temas[].citacoes[{texto, session_id}]`. `SynthesisResponse.sintese` continua sendo o `resumo` (compatível); `GET /session/{id}/synthesis` já devolve a estrutura completa. JSON inválido → 1 retry → fallback: `complete_text` antigo vira só `resumo` (sem temas).
- Síntese de roteiro: `POST /api/v1/scripts/{script_id}/sintese?refresh=false` → usa sínteses de sessão existentes do roteiro (até 30 mais recentes); < 2 → 409 "Gere a síntese de pelo menos 2 entrevistas concluídas antes do relatório do roteiro."; existente e `refresh=false` → devolve sem LLM; prompt recebe resumos/temas/citações (com `session_id`) e pede `{resumo, temas:[{tema, pontos, citacoes:[{texto, session_id}]}], divergencias:[str], lacunas:[str]}`; citações validadas contra as citações de entrada; salva `escopo="roteiro"` com id fixo `roteiro:{script_id}`. `GET /api/v1/scripts/{script_id}/sintese` → 404 "Relatório do roteiro ainda não gerado.".
- `Synthesis` ganha `divergencias: list[str] = []` e `sessoes_usadas: int = 0`.
- Excluir sessão → `pull_citations_of_session` em todas as sínteses de roteiro (`$pull` em `temas.$[].citacoes`).

- [ ] Steps: testes (RED) — Review Focus 1–3, JSON inválido → fallback, contagem `sessoes_usadas`. Implementar. Verify. Commits `feat(EV-33): sintese estruturada com citacoes conferidas`, `feat(EV-33): relatorio cruzado do roteiro`.

---

### Task 3: Backend — painel do roteiro (EV-32)

**Files:** Modify `app/repositories/session_repository.py` (pipeline do painel; reaproveitar/estender `script_stats`), `app/api/v1/endpoints/scripts.py`, `app/schemas/interview.py` ou `app/schemas/api.py` (`ScriptDashboard`). Create `tests/test_dashboard.py`.

**Interfaces:** `GET /api/v1/scripts/{script_id}/painel` → `ScriptDashboard = {script_id, titulo, total_sessoes, concluidas, em_andamento, taxa_conclusao, duracao_media_min (concluídas: updated_at − created_at), media_respostas, acoes:[{acao,total}], aprofundamentos_por_pergunta:[{pergunta_ordem, texto, media}], custo_total_usd, custo_medio_usd, temas_mais_citados:[{tema, sessoes}] (top 8, a partir de temas das sínteses de sessão, normalizando caixa/espaços), sessoes_por_dia:[{dia: "AAAA-MM-DD" fuso America/Sao_Paulo, total}] (últimos 30 dias), canais:[{canal, total}] (via $lookup em participants)}`. Um `$facet` por grupo de números; roteiro inexistente → 404.

- [ ] Steps: testes (RED) — com o seed de demonstração (`build_demo_data`) os números batem com cálculo manual em Python; roteiro vazio → zeros (Review Focus 4). Implementar. Verify. Commit `feat(EV-32): painel do roteiro com agregacoes`.

---

### Task 4: Frontend — painel e relatório cruzado (EV-32, EV-33)

**Files:** Create `src/screens/ScriptDashboardScreen.jsx` (`/entrevistas/:scriptId/painel`), `src/components/charts/BarChart.jsx`, `src/components/charts/StatTile.jsx`, `src/components/charts/DataTable.jsx`, `src/components/ScriptSynthesis.jsx`. Modify `src/services/api.js` (`getDashboard`, `getScriptSynthesis`, `generateScriptSynthesis(refresh)`), `src/App.jsx`, `src/screens/ScriptSessionsScreen.jsx` e `ScriptsScreen.jsx` (link "Painel"), `src/screens/SessionDetailScreen.jsx` (síntese estruturada: temas, pontos, citações).

**Comportamento:** linha de cards (entrevistas, taxa de conclusão, duração média, custo médio); gráficos de barras horizontais SVG (ações, aprofundamentos por pergunta, temas mais citados, canais) e colunas (sessões por dia); cada gráfico com título, legenda direta, `role="img"` + `aria-label` resumo, botão "Ver dados" (tabela); cores de tokens com contraste AA nos dois temas; números em pt-BR (`Intl.NumberFormat`), custo em USD com 4 casas. Seção "Relatório do roteiro": estado vazio com botão "Gerar relatório" (desabilitado com explicação se < 2 sínteses — usar o 409), resumo, temas com pontos e citações (cada citação é link para `/sessao/:id`), divergências e lacunas; "Gerar de novo" (refresh).

- [ ] Steps: implementar; build; conferir rotas com backend em porta livre + seed. Commits `feat(EV-32): tela do painel do roteiro`, `feat(EV-33): relatorio cruzado na tela`.

---

### Task 5: Spec e README

- [ ] EVOLUCOES: EV-32, EV-33, EV-62 → `DONE` com notas (preços configuráveis; citações conferidas). README: rotas novas, tela do painel, métricas/custo, logs estruturados, modelo de dados (`metricas` detalhado, `syntheses` com `divergencias`/`sessoes_usadas`). Commit `docs(EV-06): spec e README da fase 4`.
