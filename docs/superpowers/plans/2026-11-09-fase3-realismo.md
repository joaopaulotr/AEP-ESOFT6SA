# Fase 3 — Realismo do entrevistador: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** A conversa parece com alguém escutando de verdade: a IA reconhece o que a pessoa disse antes de perguntar, aprofunda na hora certa, respeita a persona, lembra do que foi dito, acolhe quem está mal, responde num ritmo humano (pausas, "hmm…", digitação), percebe quando a pessoa terminou de falar, para de falar quando é interrompida, e a tela mostra o estado (ouvindo / pensando / falando), legenda ao vivo e progresso.

**Architecture:** Backend: grafo LangGraph de verdade com nós separados (checagem de segurança determinística → decisão do LLM → nó por ação), prompt de escuta ativa com persona, memória e anti-repetição, limite de aprofundamentos por pergunta; turno em streaming SSE (eventos `pensando`, `frase`, `fim`) e TTS com instruções de tom. Frontend: pipeline de voz por frase (TTS da 1ª frase começa antes das outras), fillers pré-gerados, VAD e barge-in com Web Audio, onda de áudio, legenda, confirmação da transcrição, barra de progresso; modo texto com atraso dinâmico e digitação.

**Tech Stack:** FastAPI (StreamingResponse `text/event-stream`), LangGraph (`StateGraph`, `add_conditional_edges`), Pydantic v2; React 18, Web Audio API (`AnalyserNode`), `fetch` com `ReadableStream` para SSE via POST.

**Spec:** `docs/EVOLUCOES.md` — seção 5 (EV-20 a EV-26) e EV-40, EV-60, EV-80, EV-81, EV-82, EV-83. Pesquisa e fontes na seção 13.

## Global Constraints

- Rotas sob `/api/v1`; contrato atual de `POST /turn/{id}` continua funcionando (o front novo usa o stream; o antigo segue para compatibilidade e testes), só ganha campos novos.
- **Uma chamada ao LLM por turno** (latência). Segurança: checagem determinística antes do LLM + campo `risco` na resposta do LLM.
- `bash scripts/verify-delivery.sh` → `[OK]`; testes nunca chamam a OpenAI; nada de fala/perfil em log.
- Sem dependências novas no backend nem no front.
- Front: HTTP só via `src/services/api.js`; tokens; mobile; dark mode; `aria-live` na legenda; respeitar `prefers-reduced-motion` nas animações.
- Valores que a pesquisa fixa (seção 5 da spec): atraso de "pensar" entre 600 ms e 2,5 s com jitter; filler no máximo em ~50% dos turnos e nunca o mesmo duas vezes seguidas; fim de fala após ~1,2 s de silêncio; incentivo após ~12 s de silêncio total; sem erros de digitação simulados.
- Texto de acolhimento quando há risco: oferecer pausa/encerrar e citar o CVV (188, ligação gratuita, 24h, cvv.org.br).

## Review Focus

1. Pedido explícito de parar ("quero parar", "não quero mais", "chega") encerra sempre, sem depender do LLM.
2. Sinal de sofrimento/risco (ex.: falar em se machucar) → acolhimento com CVV e opção de encerrar; a entrevista não segue para a próxima pergunta como se nada fosse.
3. Pergunta que já atingiu `max_aprofundamentos` não recebe mais `deepen` (vira `advance`).
4. Stream SSE: erro do provedor no meio vira evento `erro` com mensagem em pt-BR e o turno do participante não se perde nem duplica; cliente que desconecta não deixa a sessão inconsistente.
5. Barge-in/VAD não disparam com o próprio áudio da IA (eco): usar `echoCancellation` e limiar; e o microfone é liberado ao sair da tela.

---

### Task 1: Backend — grafo real, escuta ativa, persona, memória e segurança (EV-40, EV-20, EV-21, EV-25, EV-26)

**Files:**
- Create: `app/services/interview_graph.py` (montagem do grafo e nós), `app/services/safety.py` (checagem determinística), `tests/test_interview_graph.py`, `tests/test_safety.py`.
- Modify: `app/services/interview_service.py` (usa o grafo novo), `app/prompts/interview_prompts.py`, `app/schemas/decision.py` (campos novos), `app/schemas/interview.py` (`TurnResponse` ganha campos), testes existentes do serviço.

**Interfaces (Produces):**
- `DecisionResult` ganha: `probe_tipo: Literal["elaboracao","exemplo","sentimento","clarificacao","confirmacao"] | None = None`, `risco: Literal["nenhum","sofrimento","pedido_parar"] = "nenhum"`, `reconhecimento: str = ""` (frase curta que espelha a fala da pessoa; a fala final = reconhecimento + pergunta quando não vazio e o LLM não o incluiu).
- `def check_safety(text: str) -> Literal["nenhum","sofrimento","pedido_parar"]` — regex normalizada (sem acento, minúsculas) para pedido de parar e para termos de risco (lista curta e conservadora em pt-BR). Pedido de parar tem precedência.
- Grafo (`build_interview_graph(llm) -> CompiledGraph`), estado com `interview_state`, `script`, `last_answer`, `decision`, `next_utterance`:
  `START → safety_check → (pedido_parar → encerrar_a_pedido | sofrimento → acolher | ok → decide)`; `decide → (risco≠nenhum → acolher/encerrar_a_pedido | deepen → aprofundar | advance → transicionar | finish → encerrar)`; todos → `END`.
  - `aprofundar`: se a pergunta atual já tem `max_aprofundamentos` aprofundamentos (contar turnos do entrevistador com `acao="deepen"` e a mesma `pergunta_ordem`), vira `transicionar`.
  - `transicionar`: avança `current_index`; fala = reconhecimento + transição natural + próxima pergunta (se o LLM não deu fala, usa "Entendi. " + texto da próxima pergunta). Passou da última → `encerrar`.
  - `encerrar`: fechamento personalizado (do LLM ou padrão com o nome da persona).
  - `encerrar_a_pedido`: "Tudo bem, vamos parar por aqui. Obrigado por ter conversado comigo." e `finished=True`.
  - `acolher`: mensagem de acolhimento fixa (persona) com CVV 188 + "Se quiser, a gente pode parar agora ou continuar depois." e `finished=True` (a sessão encerra por segurança; registrado no perfil `alerta="acolhimento"` sem texto da pessoa).
- Prompt (`DECISION_PROMPT`): persona (nome, tom), objetivo da pergunta, perguntas restantes, perfil e pontos já ditos (memória), últimas 3 falas do entrevistador (anti-repetição: "não repita a mesma abertura"), regras de escuta ativa (espelhar com as palavras da pessoa, tipos de probe, resposta curta/vaga/surpreendente → deepen se ainda houver aprofundamentos, linguagem oral, frases curtas, sem listas), campos JSON novos. Conteúdo da pessoa entre delimitadores e tratado como dado.
- `TurnResponse` ganha `acao`, `pergunta_ordem`, `perguntas_total`, `aprofundamentos_restantes` (opcionais com default para compatibilidade).

- [ ] Step 1: testes (RED): `check_safety` (parar, sofrimento, falso positivo comum como "parar o ônibus" não dispara — documente a escolha), cada caminho do grafo, limite de aprofundamentos, fala com reconhecimento, prompt contém persona/memória/últimas falas, Review Focus 1–3.
- [ ] Step 2: implementar. Step 3: verify backend `[OK]`. Step 4: commits `feat(EV-40): grafo de decisao com nos por acao`, `feat(EV-20): escuta ativa, persona e memoria no prompt`, `feat(EV-26): acolhimento e pedido de parar`.

---

### Task 2: Backend — turno em streaming e TTS com tom (EV-60, EV-22)

**Files:**
- Modify: `app/api/v1/endpoints/turns.py`, `app/services/session_service.py`, `app/providers/base.py` + `openai_provider.py` + `fake.py` (`synthesize(text, instructions: str | None = None)`), `app/api/v1/endpoints/voice.py` (`SpeechRequest.tom`), `app/schemas/voice.py`.
- Create: `tests/test_turn_stream.py`.

**Interfaces (Produces):**
- `POST /api/v1/turn/{session_id}/stream` (body `TurnRequest`) → `text/event-stream`. Eventos (JSON em `data:`):
  - `event: pensando` `{}` — enviado imediatamente (o front usa para filler / "digitando…").
  - `event: frase` `{"texto": "...", "indice": n}` — a fala decidida dividida em frases (`.`, `?`, `!`, `…`), na ordem.
  - `event: fim` `TurnResponse` completo.
  - `event: erro` `{"detail": "..."}` — provedor fora / conflito; com 404/409 antes de começar, responder o status HTTP normal (não SSE).
  - Cabeçalhos: `Cache-Control: no-cache`, `X-Accel-Buffering: no`.
- A gravação do turno acontece uma vez, antes de emitir `fim` (mesma regra de concorrência do turno normal).
- `def split_sentences(text: str) -> list[str]` (testado: abreviações comuns "Sr.", "Dra.", números "1.5" não quebram).
- TTS: `SpeechRequest` ganha `tom: Literal["acolhedor","neutro","formal"] | None`; `OpenAISpeechProvider.synthesize` passa `instructions` em pt-BR por tom (ex.: acolhedor: "Fale em português do Brasil, com calma e calor humano, ritmo de conversa, pausas naturais nas vírgulas."). Fake ignora.

- [ ] Step 1: testes (RED) com `TestClient` lendo o stream: ordem dos eventos, `fim` igual ao turno normal, erro do provedor vira `erro` e a sessão não fica com turno duplicado, 404/409 antes do stream. Step 2: implementar. Step 3: verify `[OK]`. Step 4: commit `feat(EV-60): turno em streaming por frase` e `feat(EV-22): voz com tom da persona`.

---

### Task 3: Frontend — voz realista (EV-22, EV-23, EV-24, EV-80, EV-81, EV-82, EV-83)

**Files:**
- Create: `src/hooks/useTurnStream.js` (POST + leitura de SSE via `ReadableStream`), `src/hooks/useVoiceActivity.js` (VAD com `AnalyserNode`: fala detectada / silêncio), `src/hooks/useFillers.js` (cache de áudios de filler), `src/components/Waveform.jsx`, `src/components/LiveCaption.jsx`, `src/components/InterviewProgress.jsx`, `src/components/TranscriptConfirm.jsx`.
- Modify: `src/services/api.js` (`streamTurn`, `synthesizeSpeech(texto, tom)`), `src/hooks/useInterviewSession.js` (usa stream; fila de áudio por frase; **ref "montado" para não agendar navegação após desmontar** — resíduo da fase 2), `src/hooks/useRecorder.js` (VAD + parada automática), `src/hooks/useAudioPlayer.js` (fila por frase, `stop()` para barge-in), `src/screens/InterviewScreen.jsx`, `src/components/Avatar.jsx`.

**Comportamento:**
- Ao enviar: evento `pensando` → se a espera passar de 700 ms, toca um filler (≤ 50% dos turnos, nunca o mesmo duas vezes seguidas; frases: "Hmm, entendi…", "Certo…", "Aham…", "Sei…", "Entendi, deixa eu pensar…", "Que interessante…"), pré-gerados com `tom` da persona na abertura da entrevista.
- Cada `frase` → pede TTS em paralelo e toca em ordem assim que a 1ª chega; a legenda mostra o texto conforme as frases tocam.
- Atraso mínimo de "pensar" (600 ms–2,5 s com jitter, proporcional ao tamanho da resposta da pessoa) antes da 1ª frase tocar.
- VAD: gravação para sozinha ~1,2 s após a pessoa parar de falar (com fala mínima de 600 ms para não cortar no começo); botão manual continua.
- Barge-in: com a IA falando, se o VAD detectar fala da pessoa por > 300 ms (com `echoCancellation: true` e limiar acima do áudio de saída), o áudio da IA para e a gravação começa.
- Silêncio total de ~12 s esperando a pessoa → mensagem "Pode ficar à vontade, sem pressa." (uma vez por pergunta).
- Onda de áudio: estados ouvindo (microfone), pensando (pulso suave), falando (saída) — `prefers-reduced-motion` desliga a animação.
- Legenda ao vivo (`aria-live="polite"`), confirmação da transcrição por 3 s com "Corrigir" (abre o texto para editar antes de enviar), barra "Pergunta 2 de 5 · aprofundando" a partir de `pergunta_ordem`/`perguntas_total`/`acao`.

- [ ] Step 1: implementar. Step 2: `npm run build`; conferir com backend em porta livre e `LLM_PROVIDER=fake`. Step 3: commits por assunto (`feat(EV-60): ...`, `feat(EV-24): ...`, `feat(EV-80): ...`, `feat(EV-23): ...`).

---

### Task 4: Frontend — texto realista (EV-22 no modo texto)

**Files:** Modify `src/screens/InterviewScreen.jsx` (modo texto), `src/components/ChatComposer.jsx`, `src/hooks/useInterviewSession.js`.

**Comportamento:** no modo texto o turno usa o stream; "digitando…" durante `pensando`; atraso dinâmico (mesma regra); cada frase é revelada em velocidade de digitação humana (~35–55 caracteres/s com jitter, micro-pausa de 250–450 ms em vírgula e 400–700 ms em ponto), sem erros de digitação; `prefers-reduced-motion` mostra o texto de uma vez; barra de progresso também no modo texto.

- [ ] Step 1: implementar. Step 2: build. Step 3: commit `feat(EV-22): ritmo de digitacao no modo texto`.

---

### Task 5: Spec e README

- [ ] `docs/EVOLUCOES.md`: EV-20, EV-21, EV-22, EV-23, EV-24, EV-25, EV-26, EV-40, EV-60, EV-80, EV-81, EV-82, EV-83 → `DONE` com nota do que foi entregue (e o que ficou de fora, se algo). README: grafo novo (mermaid), rota de stream, segurança/acolhimento, decisões de realismo com a pesquisa. Commit `docs(EV-06): spec e README da fase 3`.
