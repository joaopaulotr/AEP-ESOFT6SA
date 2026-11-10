# Fase 2 — Produto (upload, convite, modo texto): Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** O pesquisador sobe o questionário que já tem (ou cria do zero), revisa e publica o roteiro; compartilha um link/QR; o participante entra pelo link sem login e responde por voz ou por texto.

**Architecture:** Backend ganha um pipeline de importação (extratores de texto por formato → LLM estrutura e converte perguntas fechadas em abertas → rascunho que não é salvo), rotas públicas de convite (`/convite/{slug}`) que criam participante + sessão, e QR em SVG. Frontend ganha editor de roteiro (manual e a partir do upload), modal de convite com QR, fluxo público `/e/:slug` e modo texto na entrevista.

**Tech Stack:** FastAPI, Pydantic v2, Motor; novas dependências backend: `python-docx`, `pypdf`, `segno` (QR SVG puro Python). React 18 + Vite.

**Spec:** `docs/EVOLUCOES.md` — EV-30, EV-31, EV-34, EV-85 (telas do pesquisador e do participante). Plano anterior: `2026-11-09-fase1-varias-entrevistas.md` (rotas `/api/v1`, padrões de tela).

## Global Constraints

- Todas as rotas sob `/api/v1`. `bash scripts/verify-delivery.sh` termina em `[OK]` (cobertura ≥ 70% sem `omit`, build do front).
- Dependências novas **apenas**: `python-docx`, `pypdf`, `segno` (em `backend/requirements.txt`). Front: nenhuma.
- Testes nunca chamam a OpenAI; o pipeline de importação funciona offline (`LLM_PROVIDER=fake`) via fallback heurístico.
- Arquivo enviado nunca é gravado em disco nem logado; só o nome original vai para `origem.arquivo`.
- Mensagens pt-BR simples; erros: 413 tamanho, 415 tipo, 422 conteúdo, 404 convite.
- Rotas de convite são **públicas** (participante sem login) e só expõem o que o participante precisa ver (nada de outras sessões/participantes).
- Front: HTTP só via `src/services/api.js`; tokens de `tokens.css`; mobile-first; estados carregando/vazio/erro; `aria-label` em botão só de ícone.

## Review Focus

1. Arquivo grande (> `max_upload_bytes`, 2 MB) → 413 sem ler tudo para a memória; extensão/tipo fora da lista → 415.
2. PDF digitalizado (sem texto) ou arquivo sem nenhuma pergunta → 422 com mensagem clara, não 500.
3. LLM devolve JSON inválido ou sem perguntas → fallback heurístico (linhas terminadas em `?` ou numeradas) em vez de erro.
4. Convite de roteiro inativo ou slug inexistente → 404 "Convite inválido ou encerrado."; o participante não consegue listar nada além do próprio roteiro público.
5. Modo texto: resposta vazia não é enviada; alternar voz ↔ texto no meio não perde a sessão nem duplica turno.

---

### Task 1: Backend — importação de questionário (EV-30)

**Files:**
- Create: `app/importing/__init__.py`, `app/importing/extractors.py`, `app/importing/questionnaire_parser.py`, `app/prompts/import_prompts.py`, `app/services/import_service.py`, `tests/test_import_extractors.py`, `tests/test_import_service.py`, `tests/test_import_api.py`, fixtures pequenas geradas nos testes (docx/pdf criados em memória com `python-docx`/`pypdf`).
- Modify: `requirements.txt`, `app/core/config.py` (`max_upload_bytes: int = 2 * 1024 * 1024`), `app/api/v1/endpoints/scripts.py` (rota upload), `app/api/deps.py`, `app/schemas/api.py` (`ScriptDraft`, `ScriptCreate.origem`).

**Interfaces (Produces):**
- `class TextExtractor(ABC)`: `extensions: ClassVar[tuple[str, ...]]`, `def extract(self, data: bytes) -> str`. Subclasses `PlainTextExtractor` (.txt, .md), `CsvExtractor` (.csv: junta células não vazias, uma por linha), `DocxExtractor` (.docx: parágrafos + células de tabela), `PdfExtractor` (.pdf: texto de todas as páginas; texto vazio → `ImportError_("O PDF não tem texto (pode ser digitalizado).")`).
- `def extractor_for(filename: str) -> TextExtractor` → `UnsupportedFileError` (415 "Formato não suportado. Envie .txt, .md, .csv, .docx ou .pdf.").
- `class QuestionnaireParser`: `__init__(self, llm: LLMProvider)`; `async def parse(self, text: str, filename: str) -> ScriptDraft`. Usa `IMPORT_PROMPT` (converte fechada→aberta, sugere objetivo, título/tema), valida com Pydantic; JSON inválido, `ProviderError` ou zero perguntas → `heuristic_parse(text, filename)` (linhas com `?` ou numeradas `1.`/`1)`; título = nome do arquivo sem extensão). Ainda zero perguntas → `EmptyQuestionnaireError` (422 "Não encontrei perguntas no arquivo.").
- Limites: texto extraído truncado em 20.000 caracteres antes do prompt; no máximo 20 perguntas no rascunho.
- `ScriptDraft = {titulo, tema, descricao, perguntas: [{texto, objetivo}], origem: {tipo: "upload", arquivo, extraido_em}, avisos: list[str]}` (avisos ex.: "Usei a leitura automática porque a IA não respondeu.").
- `POST /api/v1/scripts/upload` (multipart `file`) → 200 `ScriptDraft` (**não salva**). Lê no máximo `max_upload_bytes + 1`; > limite → 413 "Arquivo maior que 2 MB.".
- `ScriptCreate` aceita `origem: ScriptOrigin | None` (para o front publicar o rascunho mantendo a origem).

- [ ] Step 1: testes (RED) — cada extrator, `extractor_for`, parser com LLM válido, com JSON inválido (fallback), com `ProviderError` (fallback), sem perguntas (422), rota com 413/415/422/200, e `POST /scripts` com `origem` upload gravada.
- [ ] Step 2: implementar.
- [ ] Step 3: `bash scripts/verify-delivery.sh --backend` → `[OK]`.
- [ ] Step 4: commit `feat(EV-30): importacao de questionario vira rascunho de roteiro`.

---

### Task 2: Backend — convite público e QR (EV-31, EV-34)

**Files:**
- Create: `app/api/v1/endpoints/invites.py`, `app/services/invite_service.py`, `tests/test_invites_api.py`.
- Modify: `app/core/config.py` (`frontend_url: str = "http://localhost:5173"`), `app/api/v1/endpoints/scripts.py` (QR), `app/api/v1/router.py`, `app/api/deps.py`, `app/schemas/api.py`, `backend/.env.example` (`FRONTEND_URL`).

**Interfaces (Produces):**
- `GET /api/v1/convite/{slug}` → `InvitePublic = {slug, titulo, tema, descricao, persona: {nome, tom}, perguntas_total, link}` só para roteiro **ativo**; senão 404 "Convite inválido ou encerrado.".
- `POST /api/v1/convite/{slug}/sessao` body `InviteStart = {canal: "voz"|"texto" = "voz", apelido?: str ≤ 40, faixa_etaria?: str ≤ 20, regiao?: str ≤ 60}` → cria `Participant` (campos opcionais, `canal`) + sessão no roteiro → 201 `SessionResponse` (com `titulo`, `perguntas_total`, `script_id`).
- `GET /api/v1/scripts/{script_id}/convite` → `{link: f"{frontend_url}/e/{slug}", slug}`; `GET /api/v1/scripts/{script_id}/qrcode.svg` → `image/svg+xml` do link (segno, `scale=6`, borda 2).
- `ScriptSummary` ganha `link_convite`.

- [ ] Step 1: testes (RED): convite ativo/inativo/inexistente, start cria participante com canal e sessão ligada, campos longos → 422, QR é SVG válido contendo o link (decodificar não é necessário: checar content-type e `<svg`), `link_convite` no summary.
- [ ] Step 2: implementar. Step 3: verify backend `[OK]`. Step 4: commit `feat(EV-31): convite publico com QR e entrada sem login`.

---

### Task 3: Frontend — editor de roteiro, upload e convite (EV-30, EV-31, EV-85)

**Files:**
- Create: `src/screens/ScriptEditorScreen.jsx`, `src/components/QuestionListEditor.jsx`, `src/components/InviteModal.jsx`, `src/components/FileDrop.jsx`.
- Modify: `src/services/api.js` (`uploadQuestionnaire(file)`, `createScript(data)`, `updateScript(id, data)`, `deleteScript(id)`, `getInvite(scriptId)`, `qrCodeUrl(scriptId)`), `src/App.jsx`, `src/screens/ScriptsScreen.jsx` (botões "Novo roteiro", "Subir questionário"; no card: "Convidar" abre modal com link copiável + QR; "Editar").

**Comportamento:**
- `/roteiros/novo`: editor vazio (título, tema, descrição, persona nome/tom, perguntas com objetivo e máx. aprofundamentos; adicionar, remover, subir/descer com botões acessíveis). "Publicar" → `createScript` → volta para `/entrevistas`.
- `/roteiros/importar`: `FileDrop` (arrastar ou escolher; aceita `.txt,.md,.csv,.docx,.pdf`; valida 2 MB no cliente) → "Lendo o arquivo…" → abre o editor preenchido com o rascunho + `avisos` em destaque + aviso fixo "Revise as perguntas antes de publicar." → publicar envia `origem`.
- `/roteiros/:id/editar`: carrega, `updateScript`; 409 mostra o `detail` (perguntas travadas) e mantém o formulário.
- Modal de convite: link, botão "Copiar link" (Clipboard API com fallback), imagem do QR (`qrCodeUrl`), "Abrir convite".

- [ ] Step 1: implementar. Step 2: `npm run build`; conferir as rotas da API usadas com o backend rodando numa porta livre (não matar processos alheios). Step 3: commit `feat(EV-30): editor de roteiro e importacao de questionario` e `feat(EV-31): convite com link e QR`.

---

### Task 4: Frontend — fluxo do participante e modo texto (EV-31, EV-34)

**Files:**
- Create: `src/screens/InviteScreen.jsx` (`/e/:slug`), `src/components/ChatComposer.jsx`.
- Modify: `src/App.jsx`, `src/services/api.js` (`getPublicInvite(slug)`, `startFromInvite(slug, data)`), `src/hooks/useInterviewSession.js` (aceitar sessão já criada via `?sessao=<id>` + `pergunta` inicial em `location.state`; modo `canal`), `src/screens/InterviewScreen.jsx` (modo texto + alternância), layout sem SideBar para rotas públicas.

**Comportamento:**
- `/e/:slug`: página pública acolhedora (persona: "Oi, eu sou a Ana…"), título/tema, "leva uns 10 minutos, não há resposta certa ou errada", escolha **Falar** ou **Escrever**, campos opcionais (como prefere ser chamado(a), faixa etária, cidade/bairro) com "Pular", botão Começar → `startFromInvite` → `/entrevista?sessao=<id>&canal=<canal>` (sem SideBar). Convite inválido → mensagem amigável.
- Modo texto: conversa em balões + `ChatComposer` (textarea auto-altura, Enter envia / Shift+Enter quebra linha, botão Enviar com `aria-label`, desabilitado vazio ou enviando). Entrevistador aparece com "digitando…" enquanto aguarda a resposta. Sem TTS nem microfone neste modo.
- Alternância: botão "Prefiro escrever" / "Prefiro falar" na entrevista troca o modo sem recriar a sessão.
- Participante que entra pelo convite termina numa tela de agradecimento (sem link para o painel do pesquisador).

- [ ] Step 1: implementar. Step 2: build + conferência da API. Step 3: commit `feat(EV-34): modo texto e entrada pelo convite`.

---

### Task 5: Spec e README

- [ ] `docs/EVOLUCOES.md`: EV-30, EV-31, EV-34 → `DONE`; EV-85 bullet da fase 2. README: rotas novas na tabela, telas novas, variáveis `FRONTEND_URL` e `MAX_UPLOAD_BYTES`, dependências novas. Commit `docs(EV-06): ...`.
