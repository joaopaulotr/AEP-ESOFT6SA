# Fase 1 — Várias entrevistas: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** O pesquisador escolhe um roteiro, inicia uma entrevista nele, lista as entrevistas de cada roteiro e abre a transcrição e a síntese de qualquer uma.

**Architecture:** Backend expõe CRUD de roteiros e participantes, listagem de sessões por roteiro, detalhes com `$lookup` e leitura da síntese salva — tudo sob `/api/v1`. Frontend ganha três telas (roteiros, sessões do roteiro, detalhe da sessão) e a entrevista por voz passa a receber o roteiro escolhido.

**Tech Stack:** FastAPI, Motor/MongoDB, Pydantic v2, pytest + mongomock-motor; React 18 + Vite + react-router 6, CSS tokens (`src/styles/tokens.css`).

**Spec:** `docs/EVOLUCOES.md` — EV-03 (inclusive "Pendências registradas na revisão do EV-01/EV-02"), EV-13, EV-15, EV-16, EV-85 (parte: telas do pesquisador de roteiros/sessões).

## Global Constraints

- Backend em `backend/`; testes com `backend/.venv/Scripts/python -m pytest`; `bash scripts/verify-delivery.sh` precisa terminar em `[OK]` (cobertura ≥ 70%, sem `omit`, build do front).
- Todas as rotas da API sob o prefixo `/api/v1` (EV-15); `/health` continua na raiz. O frontend muda junto (`API_PREFIX = "/api/v1"`).
- Mensagens ao usuário em pt-BR simples; `detail` de erro em pt-BR; 404/409/422 corretos, nunca 500 para entrada inválida.
- Sem dependências novas.
- Testes nunca chamam a OpenAI (dublês do `tests/conftest.py`).
- Nunca expor `_id` do Mongo; nunca logar fala/perfil de participante.
- Front: só `src/services/api.js` faz HTTP; usar os tokens de `tokens.css` (funciona em modo escuro); layout mobile-first; estados carregando / vazio / erro em toda tela nova; datas em pt-BR no fuso `America/Sao_Paulo`.

## Review Focus

1. Excluir sessão deixa síntese órfã → deve apagar em cascata (pendência EV-01/02).
2. Editar perguntas de roteiro com sessão `em_andamento` desloca quem está respondendo → 409.
3. Excluir roteiro com sessões → vira `ativo=false` (não apaga), e roteiro inativo não aceita nova sessão (já existe 409).
4. `POST /session` com `script_id` inexistente → 404 em pt-BR; sem corpo → roteiro padrão (compatível com o front antigo).
5. Pedir a síntese duas vezes não chama o LLM de novo (EV-13); `?refresh=true` regera.

---

### Task 1: Backend — rotas de roteiros, participantes, sessões e sínteses

**Files:**
- Create: `app/api/v1/endpoints/scripts.py`, `app/api/v1/endpoints/participants.py`, `app/services/script_service.py`, `app/services/participant_service.py` (só se a regra não couber no repositório), `app/schemas/api.py` (modelos de request/response novos).
- Modify: `app/main.py` (prefixo `/api/v1`), `app/api/deps.py`, `app/api/v1/endpoints/session.py`, `app/services/session_service.py`, `app/services/synthesis_service.py`, `app/repositories/base.py` (método público `upsert`), `app/db/demo_seed.py` (usar `upsert` em vez de `_collection`/`_identity`), `app/prompts/synthesis_prompts.py` + import (typo `SYNTESIS_PROMPT` → `SYNTHESIS_PROMPT`, EV-16).
- Test: `tests/test_scripts_api.py`, `tests/test_participants_api.py`, ajustes em `tests/test_endpoints.py` e demais testes de rota para o prefixo.

**Interfaces (Produces — o front da Task 2 consome exatamente isto):**
- `GET /api/v1/scripts?ativos=true` → `list[ScriptSummary]`; `ScriptSummary = {script_id, titulo, tema, descricao, slug_convite, ativo, perguntas_total: int, persona: {nome, tom}, sessoes_total: int, concluidas: int, em_andamento: int}`. Ordenado por `created_at` desc, generalista incluso. `ativos=false` lista todos.
- `GET /api/v1/scripts/{script_id}` → `InterviewScript` (404 "Roteiro não encontrado.").
- `POST /api/v1/scripts` (body `ScriptCreate = {titulo, tema?, descricao?, perguntas: [{texto, objetivo?, max_aprofundamentos?}], persona?}`; `ordem` atribuída pela posição) → 201 `InterviewScript`.
- `PUT /api/v1/scripts/{script_id}` (body `ScriptUpdate`, todos opcionais, incluindo `ativo`) → `InterviewScript`; mudar `perguntas` com sessão `em_andamento` → 409 "Este roteiro tem entrevistas em andamento; não é possível mudar as perguntas agora.".
- `DELETE /api/v1/scripts/{script_id}` → 204; sem sessões: apaga; com sessões: `ativo=false`. Roteiro padrão (`entrevista-generalista`) não pode ser apagado → 409.
- `GET /api/v1/scripts/{script_id}/sessions?status=em_andamento|concluida&limit=50` → `list[SessionSummary]`; `SessionSummary = {session_id, script_id, participant_id, participante: str | None (apelido), status, respostas: int (falas do participante), created_at, updated_at, tem_sintese: bool}`. Ordenado por `updated_at` desc.
- `GET/POST /api/v1/participants`, `GET/PUT/DELETE /api/v1/participants/{participant_id}` (body com os campos opcionais de `Participant`). DELETE com sessões → 409 (não apaga histórico).
- `POST /api/v1/session` com corpo **opcional** `{script_id?, participant_id?}` → `SessionResponse` + campos novos `script_id`, `titulo`, `perguntas_total`.
- `GET /api/v1/session/{session_id}/detalhes` → `SessionDetails` (já existe no repositório).
- `GET /api/v1/session/{session_id}/synthesis` → `Synthesis` salva (404 "Síntese ainda não gerada.").
- `POST /api/v1/session/{session_id}/synthesis?refresh=false` → `SynthesisResponse`; se já existe síntese e `refresh` falso, devolve a existente **sem chamar o LLM** (EV-13).
- `DELETE /api/v1/session/{session_id}` → 204 e apaga a síntese da sessão em cascata.
- Rotas existentes (`/session…`, `/turn…`, `/voice…`) mantêm forma, só ganham o prefixo.
- `BaseRepository.upsert(entity) -> None` (replace_one com upsert pelo `id_field`, via `_to_document`).

- [ ] Step 1: testes das rotas novas e dos 5 itens do Review Focus (RED).
- [ ] Step 2: implementar; services fazem a regra (409/cascata), rotas só traduzem.
- [ ] Step 3: `bash scripts/verify-delivery.sh --backend` → `[OK]`.
- [ ] Step 4: commits separados: `feat(EV-15): prefixo /api/v1`, `feat(EV-03): rotas de roteiros e participantes`, `feat(EV-03): sessoes por roteiro, detalhes e exclusao em cascata`, `feat(EV-13): sintese salva nao chama o LLM de novo`, `chore(EV-16): ...`.

---

### Task 2: Frontend — telas de roteiros, sessões e detalhe

**Files:**
- Create: `src/screens/ScriptsScreen.jsx`, `src/screens/ScriptSessionsScreen.jsx`, `src/screens/SessionDetailScreen.jsx`, `src/hooks/useApiResource.js` (carregando/erro/dados + recarregar), componentes pequenos em `src/components/` se repetirem (ex.: `StatusBadge.jsx`, `EmptyState.jsx`).
- Modify: `src/services/api.js` (prefixo + métodos novos), `src/App.jsx` (rotas), `src/components/SideBar.jsx` (item "Entrevistas"), `src/screens/WelcomeScreen.jsx` (botão leva a `/entrevistas`), `src/hooks/useInterviewSession.js` + `src/screens/InterviewScreen.jsx` (lê `?roteiro=<id>` e passa para `createSession`), `src/screens/FeedbackScreen.jsx` (usa síntese salva quando existir; botão "Ver entrevista" → detalhe).

**Interfaces:**
- Consumes: rotas da Task 1.
- `api`: `listScripts()`, `getScript(id)`, `listScriptSessions(scriptId, {status})`, `createSession({scriptId, participantId} = {})`, `getSessionDetails(id)`, `getSynthesis(id)` (devolve `null` em 404), `generateSynthesis(id, {refresh})`, `deleteSession(id)`.
- Rotas: `/entrevistas` (roteiros), `/entrevistas/:scriptId` (sessões), `/sessao/:sessionId` (detalhe), `/entrevista?roteiro=<id>` (entrevista por voz).

**Telas:**
- **Roteiros:** um card por roteiro — título, tema, nº de perguntas, "N concluídas · M em andamento", persona; botões "Iniciar entrevista" e "Ver entrevistas". Grid responsivo (1 coluna no celular).
- **Sessões do roteiro:** cabeçalho com o roteiro; filtro Todas / Em andamento / Concluídas; lista com data (pt-BR, fuso SP), participante ("Anônimo" se não houver), status (badge), nº de respostas, ícone se tem síntese; clique abre o detalhe. Vazio: "Nenhuma entrevista ainda" + botão iniciar.
- **Detalhe:** roteiro, participante, status, data; transcrição em balões (entrevistador × participante), com separador por pergunta central (`pergunta_ordem` → texto da pergunta do roteiro); painel de síntese: resumo, temas com pontos e citações (citação em destaque). Concluída sem síntese → botão "Gerar síntese". Em andamento → aviso "Entrevista em andamento".
- Acessibilidade: `aria-label` em botão só de ícone, foco visível, contraste via tokens.

- [ ] Step 1: api.js + rotas + telas.
- [ ] Step 2: `cd frontend && npm run build` sem erro; teste manual com o backend rodando e o seed (`python -m scripts.seed_demo`).
- [ ] Step 3: commits: `feat(EV-85): telas de roteiros, sessoes e detalhe da entrevista`, `feat(EV-15): front usa /api/v1`.

---

### Task 3: Spec

- [ ] Marcar EV-03, EV-13, EV-15 como `DONE`, EV-16 parcial (o que foi feito), EV-85 com nota "roteiros/sessões/detalhe entregues; upload, convite e dashboard nas fases 2 e 4"; pendências do EV-01/02 marcadas como resolvidas. Commit `docs: ...`.
