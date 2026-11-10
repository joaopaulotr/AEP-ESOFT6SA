# Spec de Evoluções — AEP ESOFT6S (Interviewer)

> Documento vivo. Cada item tem um ID (`EV-xx`) para ser referenciado em issues, branches, commits e PRs
> (ex.: branch `feat/EV-01-multi-colecao`, commit `feat(EV-01): ...`).
>
> Status: `TODO` · `DOING` · `DONE` · `ADIADO`

**Visão da v2:** sair de "um entrevistador com 4 perguntas fixas" para **uma plataforma de escuta em escala**:
o pesquisador sobe o próprio questionário, compartilha um link, a IA entrevista por voz (ou texto) de forma
natural, e o painel mostra o que as pessoas disseram — individualmente e no agregado.

---

## Índice

1. [Ponto de partida — v1](#1-ponto-de-partida--v1-1ª-entrega)
2. [Requisitos da 2ª entrega × situação atual](#2-requisitos-da-2ª-entrega--situação-atual)
3. [Riscos](#3-riscos)
4. [Evoluções obrigatórias](#4-evoluções-obrigatórias-2ª-entrega)
5. [Realismo do entrevistador](#5-realismo-do-entrevistador)
6. [Funcionalidades](#6-funcionalidades)
7. [Backend](#7-backend)
8. [Frontend](#8-frontend)
9. [Processo, qualidade e entrega](#9-processo-qualidade-e-entrega)
10. [Débitos técnicos do core](#10-débitos-técnicos-do-core)
11. [Fora de escopo](#11-fora-de-escopo-desta-entrega)
12. [Ordem de execução](#12-ordem-de-execução)
13. [Referências](#13-referências)

---

## 1. Ponto de partida — v1 (1ª entrega)

Versão marcada pela tag **`v0.1.0`** (`5c37a07`).

| Camada | Estado |
|---|---|
| Backend | FastAPI em camadas: `endpoints → services → repository`. DI via `Depends` (`app/api/deps.py`). |
| Core | `InterviewService.run_turn`: a cada resposta o LLM (gpt-4o-mini, JSON mode) decide `deepen` / `advance` / `finish` sobre 4 perguntas fixas (`CORE_QUESTIONS`). O grafo LangGraph tem **um nó só** (`decide`); o loop real está em Python. |
| IA | `LLMClient` (chat OpenAI), `VoiceService` (whisper-1 STT + gpt-4o-mini-tts), `SynthesisService` (relatório final). |
| Banco | MongoDB via Motor. **Uma única coleção** `interview_sessions`, com `conversation` (lista de subdocs `Turn`) e `profile` (dict). |
| Frontend | React 18 + Vite. Login (fake) → Welcome → Entrevista (voz) → Feedback (síntese). `InterviewScreen.jsx` com ~610 linhas concentra tudo; `services/api.js` não é usado. |
| Qualidade | pytest + pytest-cov; CI GitHub Actions com `--cov-fail-under=70`. Voz excluída da cobertura (`omit`). `htmlcov/` versionado manualmente. |
| Infra | docker-compose (backend, frontend, mongo:7 com healthcheck). Sem deploy público. |

---

## 2. Requisitos da 2ª entrega × situação atual

Fonte: *AEP 2026.2 6S — Engenharia de Software*, seções 6, 7, 8 (2º semestre) e 9.

| # | Critério (pts) | Exigência | Situação v1 | Itens |
|---|---|---|---|---|
| R1 | PoC funcional e evolução (0,1) | Fluxos principais OK + evolução verificável vs. 1ª entrega | Fluxo OK; evolução a fazer | Toda a spec; comparação `v0.1.0` → `v2.0.0` |
| R2 | Banco NoSQL (0,1) | **Múltiplas coleções**, **relacionamento entre coleções**, ≥1 coleção com **objetos complexos** | ❌ 1 coleção. Aninhamento OK | **EV-01, EV-02, EV-03** |
| R3 | POO e qualidade (0,1) | Responsabilidades claras, sem duplicação/acoplamento relevante | Bom, com débitos | EV-02, EV-41, seção 10 |
| R4 | Metodologia (0,1) | **Quadro de tarefas** | ❌ inexistente | **EV-04** |
| R5 | Testes automatizados (0,1) | Conjunto pertinente, comportamentos relevantes | Bom; voz fora | EV-05, EV-70 |
| R6 | Cobertura ≥ 70% (0,1) | Evidência reproduzível | CI falha < 70% ✅ | EV-05 |
| R7 | Documentação técnica (0,1) | Instalar, executar, testar, **tecnologias e estrutura do banco** | README bom; falta banco | **EV-06** |
| R8 | GitHub e versionamento (0,1) | Histórico coerente, **versão final identificável** | `v0.1.0` ✅; falta final | **EV-07** |
| R9 | Vídeo 3–5 min (0,2) | Evolução, arquitetura final, demo, tecnologias, testes/cobertura, resultados | — | **EV-08** |

---

## 3. Riscos

| ID | Risco | Impacto | Prob. | Mitigação |
|---|---|---|---|---|
| RK-01 | **Requisito NoSQL do 2º semestre não atendido** — hoje só existe `interview_sessions` | Zera R2 e enfraquece R1 | Alta se não priorizado | EV-01..EV-03 são os primeiros itens de código. Nenhuma feature nova entra antes. |
| RK-02 | **Sem quadro de tarefas** | Zera R4 (0,1) — ponto "grátis" perdido | Alta | EV-04 na semana 1; issues retroativas para o que já foi feito. |
| RK-03 | **Voz excluída da cobertura** (`omit` em `pyproject.toml`) | Banca pode considerar a cobertura "maquiada" | Média | EV-05: testes da voz com cliente OpenAI mockado e remoção do `omit`. — **mitigado** (feat/EV-41-core-providers) |
| RK-04 | **`htmlcov/` versionado à mão fica desatualizado** (já contém `syntesis_service.py`, que não existe mais) | Evidência de cobertura incoerente com o código | Alta | EV-05: gerar no CI e publicar como artefato/GitHub Pages; remover `htmlcov/` do repo. |
| RK-05 | **Escopo grande para equipe de 3** | Entrega incompleta ou com bugs | Alta | Ordem da seção 12; obrigatórios primeiro; features marcadas como cortáveis. |
| RK-06 | **Dependência da OpenAI na demo** (custo, rate limit, queda, latência) | Demo falha ao vivo | Média | EV-61 (provider fake), vídeo gravado com fallback, chave com limite de gasto, EV-62 (métricas de custo). — provider fake disponível (`LLM_PROVIDER=fake`) |
| RK-07 | **Saída do LLM não validada** — JSON incompleto → 500; `profile_updates` não-string corrompe a sessão | Entrevista quebra no meio da demo | Média | EV-11 (schema Pydantic + retry + fallback). — **mitigado** (feat/EV-41-core-providers) |
| RK-08 | **Latência alta da voz** (STT → LLM → TTS em série, chamadas síncronas) | Experiência "robótica", contradiz o objetivo de realismo | Alta | EV-10 (async), EV-60 (streaming), seção 5 (fillers e masking). |
| RK-09 | **Transcrição pior com sotaques regionais / fala fora da norma culta** | Atinge justamente o público da ODS 10 | Média | Prompt de domínio no whisper, confirmação da transcrição na tela (EV-82), modo texto (EV-34). Declarar no README como limite. |
| RK-10 | **Viés do LLM na síntese** | Relatório distorce o que foi dito | Média | Síntese com citações literais obrigatórias e instrução de não inventar; mostrar trecho de origem (EV-33). |
| RK-11 | **Dados pessoais de participantes sem proteção** (CORS `*`, sem auth, `session_id` expõe transcrição) | Exposição de dados; questionamento ético | Média | Participante sem identificação obrigatória; CORS restrito no deploy (EV-71); auth adiada declarada como limite. |
| RK-12 | **Upload de questionário malformado** (PDF escaneado, formato inesperado) | Roteiro errado ou vazio | Média | EV-30: revisão humana obrigatória antes de publicar; limite de tamanho/tipo. |
| RK-13 | **Deploy público instável perto da apresentação** | Demo indisponível | Baixa | EV-71 cedo (não no último dia); docker-compose local como plano B. |
| RK-14 | **Branch de trabalho divergente da `main`** (hoje `devjoao` vs `main`) | Conflitos e versão final confusa | Média | Fluxo por PR curto para `main`; tag final só na `main`. |

---

## 4. Evoluções obrigatórias (2ª entrega)

### EV-01 — Modelagem multi-coleção `TODO` · bloqueante (R2, RK-01)

Transforma o roteiro fixo em dado e separa participante de sessão.

```
interview_scripts (roteiros/campanhas)      participants
  script_id                                   participant_id
  titulo, tema, descricao                     apelido?, faixa_etaria?, regiao?
  origem: {tipo: manual|upload,               canal: voz|texto
           arquivo?, extraido_em?}            created_at
  perguntas: [ {ordem, texto, objetivo,
                max_aprofundamentos} ]  ◄─ lista de subdocs
  persona: {nome, tom}
  slug_convite, ativo, created_at
        ▲                                         ▲
        │ script_id                               │ participant_id
        └─────────────── interview_sessions ──────┘
                           session_id
                           script_id      (ref)
                           participant_id (ref)
                           conversation: [ {role, text, timestamp,
                                            pergunta_ordem, acao,
                                            latencia_ms} ]  ◄─ subdocs
                           profile: {…}
                           metricas: {tokens, segundos_audio, custo_usd}
                           current_index, status, created_at, updated_at
                                   │ session_id
                                   ▼
                           syntheses
                             session_id? (ref) | script_id (ref)
                             escopo: sessao | roteiro
                             resumo
                             temas: [ {tema, pontos: [...],
                                       citacoes: [ {texto, session_id} ]} ]
                             lacunas: [...], modelo, created_at
```

- 4 coleções, relacionamentos por referência, subdocumentos em 3 coleções.
- `CORE_QUESTIONS` vira o roteiro *seed* "Entrevista generalista".
- `InterviewService` passa a receber o `InterviewScript` em vez de ler constante.

### EV-02 — Repositórios por agregado + base genérica `TODO` (R2, R3)

- `BaseRepository[T]` com CRUD genérico (`create/get/save/delete/list`) — herança e genéricos aplicados de fato.
- `ScriptRepository`, `ParticipantRepository`, `SessionRepository`, `SynthesisRepository`.
- Índices criados no `lifespan`: `session_id` único, `script_id`, `participant_id`, `slug_convite` único.
- Consulta relacional com `$lookup`: sessão → participante + roteiro.
- Aggregation pipelines para o dashboard (EV-32).

### EV-03 — Endpoints CRUD das novas coleções `TODO` (R2)

| Recurso | Rotas |
|---|---|
| Roteiros | `GET/POST /scripts`, `GET/PUT/DELETE /scripts/{id}`, `POST /scripts/upload` (EV-30) |
| Participantes | `GET/POST /participants`, `GET/PUT/DELETE /participants/{id}` |
| Sessões | `POST /session` recebe `script_id` (+ `participant_id` opcional); `GET /scripts/{id}/sessions`; `GET /sessions/{id}/detalhes` (`$lookup`) |
| Sínteses | `GET /syntheses/session/{id}`, `POST /syntheses/script/{id}` (EV-33) |

Todas sob o prefixo `/api/v1` (EV-15).

### EV-04 — Quadro de tarefas `TODO` (R4, RK-02)

- GitHub Projects (Kanban: Backlog → To Do → Doing → Review → Done).
- 1 issue por `EV-xx`, linkada ao PR. Labels: `obrigatorio`, `back`, `front`, `infra`, `realismo`.
- Print do quadro + link no README (seção "Metodologia").

### EV-05 — Testes e evidência de cobertura `TODO` (R5, R6, RK-03, RK-04)

- Testes para todos os novos repositórios, services e endpoints.
- Voz coberta com cliente OpenAI mockado → **remover o `omit`**.
- CI gera `htmlcov` e publica como artefato (e/ou GitHub Pages); **remover `backend/htmlcov/` do repo**.
- Badge de cobertura no README; comando documentado: `cd backend && pytest --cov-report=html`.
- ✅ Voz já entra na cobertura (omit removido em `pyproject.toml`).

### EV-06 — Documentação técnica `TODO` (R7)

- `docs/banco.md`: coleções, documento de exemplo real de cada uma, relacionamentos, índices, pipelines.
- `docs/arquitetura.md`: diagrama de componentes, diagrama de sequência de um turno, grafo LangGraph final.
- `docs/api.md` ou link para o Swagger (`/docs`) com exemplos.
- README: seção "Evolução v1 → v2" com tabela do que mudou + seção "Limites" atualizada.

### EV-07 — Versionamento identificável `TODO` (R8)

- `v0.1.0` já marca a 1ª entrega ✅.
- Tag `v2.0.0` + GitHub Release na versão final, com notas.
- `CHANGELOG.md` por versão.

### EV-08 — Vídeo 3–5 min `TODO` (R9)

Roteiro: problema/ODS (30s) → v1 vs v2 (40s) → arquitetura + modelo do banco (60s)
→ demo ao vivo: upload de questionário → link → entrevista por voz → dashboard (90s)
→ testes + cobertura no CI (30s) → resultados, custo por entrevista e limites (30s).

---

## 5. Realismo do entrevistador

Objetivo: a conversa precisa **parecer com alguém escutando de verdade** — não um formulário que fala.
Pesquisa resumida (fontes na seção 13):

- Em conversa humana a troca de turno acontece em menos de 1 s; **acima de ~4 s a experiência degrada**, e
  **fillers conversacionais melhoram a percepção de tempo de resposta**, principalmente com latência alta.
- **Atrasos dinâmicos proporcionais à complexidade da resposta** aumentam a percepção de humanidade e a
  satisfação; resposta instantânea parece "irreal". Indicador de digitação atenua o efeito negativo da latência.
- Em entrevista por IA, a falha mais comum é **não fazer follow-up depois de uma resposta surpreendente ou vaga**;
  o difícil é o equilíbrio entre aprofundar demais e de menos.
- Backchannel ("uhum", "entendi") ajuda, mas **em excesso soa performático/debochado**.
- Erros de digitação simulados **reduzem** a humanidade percebida; hesitação e autocorreção pontual são bem vistas.

### EV-20 — Escuta ativa no prompt de decisão `TODO`

- O entrevistador **reconhece o que a pessoa disse antes de perguntar** (espelhamento curto com as palavras dela:
  "Você falou que o ônibus atrasa toda semana…").
- Tipos de probe explícitos no prompt: **elaboração** ("me conta mais"), **exemplo concreto** ("como foi da última vez?"),
  **sentimento** ("e como você se sentiu?"), **clarificação** ("quando você diz X, quer dizer…?"), **confirmação**.
- Regra: resposta curta, vaga ou surpreendente → `deepen` obrigatório (até `max_aprofundamentos` da pergunta).
- Transição natural entre perguntas centrais ("Entendi. Mudando um pouco de assunto…"), sem ler o roteiro literalmente.
- Linguagem oral, frases curtas, sem listas, sem jargão; adaptar o registro ao do participante.
- Anti-repetição: não repetir a mesma abertura/estrutura em turnos seguidos (histórico das últimas falas no prompt).

### EV-21 — Persona configurável `TODO`

- Nome, tom (acolhedor/neutro/formal) e voz TTS por roteiro (`interview_scripts.persona`).
- Apresentação inicial humana: quem é, quanto tempo leva, que não existe resposta certa.

### EV-22 — Ritmo humano (timing) `TODO`

- **Atraso dinâmico**: tempo de "pensar" proporcional ao tamanho da resposta do participante e da próxima fala,
  com jitter aleatório (ex.: 600 ms–2,5 s), nunca resposta instantânea.
- **Modo texto:** indicador "digitando…" + texto revelado em velocidade de digitação humana (via streaming, EV-60),
  com micro-pausas em vírgulas/pontos. Sem erros de digitação simulados.
- **Modo voz:** pausas naturais (vírgulas e reticências no texto enviado ao TTS) e instruções de entonação no
  `gpt-4o-mini-tts` (ex.: "fale de forma calma, calorosa, como numa conversa").

### EV-23 — Backchannel e fillers `TODO`

- Enquanto o LLM processa, tocar um **filler curto e contextual** ("hmm, entendi…", "certo…") — pré-gerado em
  cache de áudio para latência zero, sorteado sem repetir o último.
- Frequência limitada (não em todo turno) para não soar performático.
- Filler gerado em paralelo por sub-prompt rápido quando a resposta for longa/emocional.

### EV-24 — Turn-taking `TODO`

- **Detecção de fim de fala (VAD)** no navegador: para de gravar após silêncio (~1,2 s) em vez de exigir clique.
- **Barge-in**: se o participante começa a falar enquanto a IA fala, o áudio da IA para.
- Silêncio longo do participante → incentivo gentil ("pode ficar à vontade, sem pressa").

### EV-25 — Memória e coerência `TODO`

- Perfil extraído (`profile`) e pontos-chave já ditos entram no prompt → a IA retoma coisas ditas antes
  ("Lá no começo você comentou que trabalha à noite…") e não pergunta o que já foi respondido.
- Encerramento personalizado, citando 1–2 pontos da conversa e agradecendo.

### EV-26 — Cuidado (safety) `TODO`

- Nó `safety_check` (EV-40) detecta sofrimento, risco ou pedido para parar → responde com acolhimento,
  oferece pausar/encerrar e (se for o caso) indica canal de ajuda (ex.: CVV 188).
- Pedido explícito de parar encerra sempre.

---

## 6. Funcionalidades

### EV-30 — Upload de questionário → roteiro `TODO`

O pesquisador **sobe o questionário que já tem** e a plataforma transforma em roteiro de entrevista.

- Formatos: `.txt`, `.md`, `.csv`, `.docx`, `.pdf` (texto). Limite de tamanho; PDF escaneado → erro claro.
- Pipeline: extração de texto → LLM estrutura em `{titulo, tema, perguntas[{texto, objetivo}]}` →
  **converte perguntas de formulário em perguntas abertas de entrevista** (ex.: "Você usa transporte público? (S/N)"
  → "Me conta como é seu deslocamento no dia a dia") e sugere o objetivo de cada uma.
- **Revisão humana obrigatória**: tela de edição (reordenar, editar, remover, adicionar) antes de publicar (RK-12).
- Também é possível criar roteiro do zero no mesmo editor.
- Arquivo original referenciado em `interview_scripts.origem`.

### EV-31 — Link de convite por roteiro `TODO`

- Cada roteiro publicado gera `/e/{slug}` + QR code.
- Participante entra direto, sem login, escolhe voz ou texto e começa.

### EV-32 — Dashboard do pesquisador `TODO`

- Por roteiro: nº de sessões, taxa de conclusão, duração média, nº médio de aprofundamentos por pergunta,
  distribuição de ações (`deepen/advance/finish`), custo médio por entrevista (EV-62), temas mais citados.
- Implementado com **aggregation pipelines** do MongoDB (`$group`, `$unwind`, `$lookup`) — reforça R2.
- Lista de sessões com acesso à transcrição e à síntese individual.

### EV-33 — Síntese cruzada por roteiro `TODO`

- Relatório agregado de todas as sessões concluídas de um roteiro: padrões, divergências, temas, citações
  literais com link para a sessão de origem, lacunas.
- Salvo em `syntheses` com `escopo: roteiro`. Map-reduce: usa as sínteses individuais já salvas como entrada.
- Síntese individual passa a ser estruturada (JSON → `temas[]`, `citacoes[]`) e cacheada (EV-13).

### EV-34 — Modo texto `TODO`

- Alternativa à voz para quem não pode/não quer falar ou tem deficiência auditiva (ODS 10).
- Mesmo backend de turnos; UI de chat com realismo de digitação (EV-22).
- Alternância voz ↔ texto durante a entrevista.

---

## 7. Backend

### EV-40 — Grafo LangGraph real `TODO`

```
START → extract_profile → safety_check ─┬─ risco → acolher_e_encerrar → END
                                        └─ ok → decide ─┬─ deepen  → gerar_probe   → END
                                                        ├─ advance → transicionar  → END
                                                        └─ finish  → encerrar      → END
```

- Arestas condicionais; cada nó com responsabilidade única e testável isoladamente.
- O loop deixa de viver em `run_turn` (substitui EV-14 da versão anterior desta spec).

### EV-41 — Abstração `LLMProvider` `DONE` (R3)

- Interface (ABC/`Protocol`) `LLMProvider` com `complete_json`, `complete_text`, `stream_text`;
  `SpeechProvider` com `transcribe`, `synthesize`.
- Implementações: `OpenAIProvider` e `FakeProvider` (determinística, usada em testes/E2E/demo offline — RK-06).
- Escolha por configuração. Demonstra polimorfismo para Paradigmas de Linguagem.
- `stream_text` fica para o EV-60 (streaming), quando houver consumidor.

### EV-60 — Streaming da fala (SSE) `TODO`

- `POST /api/v1/turn/{id}/stream` devolve Server-Sent Events: tokens do texto conforme gerados;
  TTS por frase assim que a primeira frase fecha → áudio começa antes da resposta inteira existir (RK-08).
- Base para o efeito de digitação do modo texto (EV-22).

### EV-62 — Logs estruturados e métricas de custo `TODO`

- Log JSON por request (session_id, nó do grafo, latência por etapa STT/LLM/TTS).
- Tokens e segundos de áudio por turno → `interview_sessions.metricas`, custo estimado em USD.
- Alimenta o dashboard e o argumento de "custo marginal perto de zero" no vídeo com números reais.

---

## 8. Frontend

### EV-80 — Estados visuais e onda de áudio `TODO`

- Avatar com estados claros: **ouvindo** (onda reage ao microfone via Web Audio `AnalyserNode`),
  **pensando** (animação sutil), **falando** (onda do áudio da IA).

### EV-81 — Transcrição ao vivo `TODO`

- Painel lateral estilo legenda com a conversa; fala da IA aparece em streaming.

### EV-82 — Confirmação da transcrição `TODO`

- Após transcrever, mostra o texto por alguns segundos com opção "corrigir" antes de enviar (RK-09).

### EV-83 — Barra de progresso do roteiro `TODO`

- "Pergunta 2 de 5 · aprofundando" — reduz ansiedade e abandono.

### EV-84 — Design system, dark mode e mobile-first `DONE`

- Tokens cobrem cor, fonte, sombra e área de toque; espaçamentos continuam nos estilos de cada tela.
- Tema escuro via `data-theme` no `<html>`, escolha salva no navegador e botão no menu lateral (`ThemeToggle` + `useTheme`).
- Layout mobile-first (o público da ODS 10 acessa principalmente pelo celular); áreas de toque grandes.
- Acessibilidade: contraste AA, foco visível, `aria-live` na transcrição.

### EV-85 — Telas novas `TODO`

- Pesquisador: lista de roteiros, editor/upload (EV-30), dashboard (EV-32), sessão (transcrição + síntese),
  síntese cruzada (EV-33).
- Participante: entrada pelo convite (EV-31), escolha voz/texto, entrevista, agradecimento.


### EV-17 — Refatoração da `InterviewScreen` `DONE`

- Hooks: `useRecorder` (MediaRecorder + VAD), `useAudioPlayer` (fila + barge-in), `useInterviewSession`, `useTurnStream` (SSE).
- Client HTTP único em `services/api.js`; nada de `fetch` espalhado nas telas.

Decisões da implementação:

- Hooks feitos: `useInterviewSession`, `useRecorder`, `useAudioPlayer`, `useElapsedTime`. Formatação de hora em `utils/tempo.js` e estilos em `InterviewScreen.styles.js`.

---

## 9. Processo, qualidade e entrega

### EV-70 — Testes E2E com Playwright `TODO`

- Fluxos: upload de questionário → publicar → entrevista (modo texto) → síntese → dashboard.
- Backend com `FakeProvider` (EV-41) → testes determinísticos, sem custo de OpenAI.
- Roda no CI com docker-compose.

### EV-71 — Deploy público `TODO`

- Railway (backend + frontend + MongoDB). URL pública no README e na entrega.
- CORS restrito ao domínio do front; chave OpenAI com limite de gasto (RK-06, RK-11, RK-13).
- Deploy automático a partir da `main`.

### EV-72 — CI do frontend `TODO`

- Workflow `frontend-ci.yml`: `npm ci`, ESLint, `vite build` (e E2E do EV-70).

---

## 10. Débitos técnicos do core

| ID | Problema | Correção |
|---|---|---|
| EV-10 | Chamadas OpenAI **síncronas** em endpoints `async` bloqueiam o event loop | `AsyncOpenAI`; services `async` (dentro do `OpenAIProvider`, EV-41) ✅ DONE |
| EV-11 | Saída do LLM não validada: `result["action"]` → KeyError; ação inválida vira `deepen` silencioso; `profile_updates` não-string corrompe a sessão | Modelo Pydantic `DecisionResult` + retry + fallback determinístico ✅ DONE. Decisão: fallback no último turno encerra; a resposta fica na transcrição e entra na síntese (evita prender a pessoa em loop com provedor fora do ar). |
| EV-12 | `deps.py` recria service, cliente OpenAI e recompila o grafo a cada request | Singletons via `lru_cache` / `lifespan` ✅ DONE |
| EV-13 | `/synthesis` regenera (e paga) a cada chamada | Retornar existente; `?refresh=true` para regerar |
| EV-15 | Rotas sem prefixo apesar da pasta `api/v1` | `include_router(prefix="/api/v1")` |
| EV-16 | Typo `SYNTESIS_PROMPT`; `remaining_questions` como repr de lista; `asked_indices` redundante; `bash.exe.stackdump` commitado; `api.js` não usado | Limpeza |

---

## 11. Fora de escopo desta entrega

| Item | Motivo |
|---|---|
| Termo de consentimento LGPD / exportação e exclusão de dados | Decisão da equipe; declarado como limite no README |
| Exportar síntese em PDF/Markdown | Adiado |
| Autenticação real (JWT) do pesquisador | Adiado; área do pesquisador sem login na PoC, declarado como limite (RK-11) |

---

## 12. Ordem de execução

| Fase | Itens | Por quê |
|---|---|---|
| 0 — Fundação | EV-04, EV-16, EV-15, EV-12 | Quadro de tarefas (ponto garantido) e casa arrumada |
| 1 — Obrigatório NoSQL | EV-01, EV-02, EV-03, EV-41 | Maior risco (RK-01); provider fake destrava testes |
| 2 — Core robusto | EV-10, EV-11, EV-40, EV-13 | Base para realismo e demo estável |
| 3 — Produto | EV-30, EV-31, EV-34, EV-85, EV-17 | Fluxo novo ponta a ponta |
| 4 — Realismo | EV-20..EV-26, EV-60, EV-80..EV-83 | O "uau" da demo |
| 5 — Visão do pesquisador | EV-32, EV-33, EV-62 | Resultados para o vídeo |
| 6 — Polimento | EV-84, EV-70, EV-72, EV-71 | Qualidade e demo pública |
| 7 — Entrega | EV-05, EV-06, EV-07, EV-08 | Testes/docs acompanham cada fase; aqui só fecha |

**Cortáveis se faltar tempo** (nesta ordem): EV-23 parte gerada por sub-prompt, EV-82, EV-33, EV-24 barge-in, EV-70.

---

## 13. Referências

- AEP 2026.2 6S — Engenharia de Software (enunciado da atividade).
- Gnewuch et al., *Faster is Not Always Better: Understanding the Effect of Dynamic Response Delays in Human-Chatbot Interaction*, ECIS 2018 — https://aisel.aisnet.org/ecis2018_rp/113/
- *Beyond Words: Infusing Conversational Agents with Human-like Typing Behaviors* — https://arxiv.org/abs/2510.08912
- *AI Conversational Interviewing: Transforming Surveys with LLMs as Adaptive Interviewers* — https://arxiv.org/abs/2410.01824
- *AI-Assisted Conversational Interviewing: Effects on Data Quality and Respondent Experience* — https://arxiv.org/abs/2504.13908
- *Chatbots for Data Collection in Surveys: A Comparison of Four Theory-Based Interview Probes* — https://arxiv.org/abs/2503.08582
- Estudo sobre latência e fillers em agentes de voz (UCF) — https://www.eecs.ucf.edu/isuelab/publications/pubs/maslychmCUI25.pdf
- Picovoice, *Voice UX: Latency, Turn-Taking, and Barge-In* — https://picovoice.ai/guide/voice-agents/voice-ux-latency-turn-taking/
- Retell AI, *Turn-Taking in Voice AI* — https://www.retellai.com/blog/turn-taking-voice-ai-hidden-problem
