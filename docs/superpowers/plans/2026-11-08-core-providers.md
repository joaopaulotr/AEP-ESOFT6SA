# Core: Providers, Async e Decisão Validada — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar o acesso direto à OpenAI por providers abstratos e assíncronos (com implementação fake para testes/demo offline), validar a decisão do LLM com retry e fallback, e transformar as dependências em singletons — sem mudar o contrato HTTP usado pelo frontend.

**Architecture:** Novo pacote `app/providers/` com as ABCs `LLMProvider` e `SpeechProvider`, implementações `OpenAI*` (via `AsyncOpenAI`) e `Fake*` (determinísticas), e uma factory escolhida por `settings.llm_provider`. Services passam a ser `async` e recebem o provider por injeção (obrigatória). A saída do LLM é validada por `DecisionResult` (Pydantic); falha → 1 retry → fallback `advance`. `deps.py` cacheia providers e services com `lru_cache`.

**Tech Stack:** Python 3.11, FastAPI, openai 1.x (`AsyncOpenAI`), LangGraph (`ainvoke` com nó async), Pydantic v2, pytest + anyio + pytest-cov.

**Spec:** `docs/EVOLUCOES.md` — itens **EV-41**, **EV-10**, **EV-11**, **EV-12** (e o `omit` da voz de EV-05/RK-03, porque a voz fica testável aqui).

## Global Constraints

- Trabalhar em `backend/`; todos os comandos rodam de `backend/`.
- **Nenhuma dependência nova** em `requirements*.txt` (`AsyncOpenAI` vem do `openai`, `ainvoke` do `langgraph`).
- **Contrato HTTP inalterado:** mesmas rotas, mesmos campos de request/response (`fala`, `finalizada`, `indice_atual`, `session_id`, `pergunta`, `sintese`, `texto`). Prefixo `/api/v1` é EV-15, fora deste plano.
- **Não tocar** em `app/repositories/`, `app/schemas/interview.py`, `app/db/` (área da Pessoa A — EV-01/02/03).
- Mensagens para o usuário em **português**.
- Testes nunca acessam a rede: o fixture autouse do `conftest.py` deve explodir se o cliente OpenAI real for construído.
- Cobertura: `pytest --cov-fail-under=70` passa **sem** o `omit` da voz.
- Commits no formato `feat(EV-xx): ...` / `refactor(EV-xx): ...` / `test(EV-xx): ...`, em português.
- Branch: `feat/EV-41-core-providers` a partir de `devjoao` atualizada.

## Review Focus

1. LLM devolve JSON **sem `action`** ou com ação inválida (`"skip"`) → a entrevista segue (retry, depois fallback `advance`), nunca 500. → Task 4.
2. `profile_updates` com valores **não-string** (número, lista, `null`, objeto) → coagidos/descartados; a sessão salva **recarrega** do repositório sem `ValidationError`. → Task 2 + Task 4.
3. OpenAI **fora do ar/timeout**: no turno → fallback após retry; na síntese e na voz → **HTTP 502** com `detail` em português, não 500. → Task 3 e Task 5.
4. **Upload de áudio vazio** em `/voice/transcricao` → 400 `"Áudio vazio."`, sem chamar o provider. → Task 5.
5. Overrides de dependência continuam funcionando com `lru_cache` e o cache **não vaza entre testes** (instância fake vs openai trocada por config). → Task 6.

---

## File Structure

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `app/providers/__init__.py` | Create | Reexporta ABCs, `ProviderError`, factories |
| `app/providers/base.py` | Create | `ProviderError`, `LLMProvider`, `SpeechProvider` (ABCs async) |
| `app/providers/fake.py` | Create | `FakeLLMProvider`, `FakeSpeechProvider` determinísticos |
| `app/providers/openai_provider.py` | Create | `OpenAILLMProvider`, `OpenAISpeechProvider` (AsyncOpenAI) |
| `app/providers/factory.py` | Create | `build_llm_provider(settings)`, `build_speech_provider(settings)` |
| `app/schemas/decision.py` | Create | `DecisionResult` |
| `app/core/config.py` | Modify | `llm_provider`, `llm_model` |
| `app/services/interview_service.py` | Modify | async, `llm: LLMProvider`, validação + retry + fallback |
| `app/services/synthesis_service.py` | Modify | async provider, `llm: LLMProvider` |
| `app/services/llm_client.py` | Delete | substituído por `OpenAILLMProvider` |
| `app/services/voice_service.py` | Delete | substituído por `SpeechProvider` |
| `app/api/deps.py` | Modify | providers + services em `lru_cache` |
| `app/api/v1/endpoints/*.py` | Modify | `await` nos services; voz usa `SpeechProvider` |
| `app/main.py` | Modify | handler `ProviderError` → 502 |
| `pyproject.toml` | Modify | remover `omit` da voz |
| `.env.example` | Modify | `LLM_PROVIDER=openai` |
| `tests/conftest.py` | Modify | dublês async; autouse bloqueia `AsyncOpenAI` real |
| `tests/test_providers_fake.py`, `tests/test_openai_provider.py`, `tests/test_decision.py`, `tests/test_voice_endpoints.py`, `tests/test_deps.py` | Create | — |
| `tests/test_llm_client.py` | Delete | migra para `test_openai_provider.py` |
| `tests/test_interview_service.py`, `tests/test_synthesis_service.py`, `tests/test_endpoints.py` | Modify | async + nova injeção |

---

### Task 1: Interfaces, providers fake, providers OpenAI e factory

Cria o pacote `app/providers/` completo, ainda sem ninguém consumir. O código antigo (`LLMClient`, `VoiceService`) continua intacto; a suíte inteira segue verde.

**Files:**
- Create: `app/providers/__init__.py`, `app/providers/base.py`, `app/providers/fake.py`, `app/providers/openai_provider.py`, `app/providers/factory.py`
- Modify: `app/core/config.py`, `.env.example`, `tests/conftest.py`
- Test: `tests/test_providers_fake.py`, `tests/test_openai_provider.py`

**Interfaces:**
- Produces:
  - `class ProviderError(Exception)` — falha de provedor (rede, API, JSON inválido).
  - `class LLMProvider(ABC)`: `async def complete_json(self, prompt: str) -> dict`, `async def complete_text(self, prompt: str) -> str` (abstratos).
  - `class SpeechProvider(ABC)`: `async def transcribe(self, audio: bytes, filename: str = "audio.webm") -> str`, `async def synthesize(self, text: str) -> bytes` (abstratos).
  - `FakeLLMProvider()`; `FAKE_DECISION: dict = {"action": "advance", "next_utterance": "", "profile_updates": {}, "closing_statement": ""}`; `FAKE_SYNTHESIS = "Síntese gerada em modo offline (provider fake)."`
  - `FakeSpeechProvider()`; `FAKE_TRANSCRIPTION = "Resposta simulada em modo offline."`; `synthesize` devolve `b""`.
  - `OpenAILLMProvider(client: AsyncOpenAI | None = None, model: str = "gpt-4o-mini")`
  - `OpenAISpeechProvider(client: AsyncOpenAI | None = None, transcription_model: str = "whisper-1", speech_model: str = "gpt-4o-mini-tts", voice: str = "alloy")`
  - `build_llm_provider(settings: Settings) -> LLMProvider`, `build_speech_provider(settings: Settings) -> SpeechProvider`
  - `Settings.llm_provider: Literal["openai", "fake"] = "openai"`, `Settings.llm_model: str = "gpt-4o-mini"`
  - conftest: `FakeAsyncOpenAI` (dublê async do SDK com `chat.completions.create`, `audio.transcriptions.create`, `audio.speech.create`), fixture `fake_async_openai`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_providers_fake.py` (`pytestmark = pytest.mark.anyio`):
```python
async def test_fake_llm_returns_the_fixed_advance_decision():
    assert await FakeLLMProvider().complete_json("qualquer") == FAKE_DECISION
    assert FAKE_DECISION["action"] == "advance"

async def test_fake_llm_returns_a_copy_each_time():
    provider = FakeLLMProvider()
    first = await provider.complete_json("p"); first["action"] = "finish"
    assert (await provider.complete_json("p"))["action"] == "advance"

async def test_fake_llm_text_is_the_offline_synthesis():
    assert await FakeLLMProvider().complete_text("p") == FAKE_SYNTHESIS

async def test_fake_speech_transcribes_to_the_fixed_text():
    assert await FakeSpeechProvider().transcribe(b"abc", "a.webm") == FAKE_TRANSCRIPTION

async def test_fake_speech_synthesizes_empty_audio():
    assert await FakeSpeechProvider().synthesize("olá") == b""

def test_providers_are_abstract():
    with pytest.raises(TypeError): LLMProvider()
    with pytest.raises(TypeError): SpeechProvider()

def test_factory_builds_fake_providers():
    s = Settings(llm_provider="fake")
    assert isinstance(build_llm_provider(s), FakeLLMProvider)
    assert isinstance(build_speech_provider(s), FakeSpeechProvider)

def test_settings_rejects_unknown_provider():
    with pytest.raises(ValidationError): Settings(llm_provider="gemini")
```

`tests/test_openai_provider.py` (`pytestmark = pytest.mark.anyio`) — portar **todos** os casos de `tests/test_llm_client.py` para `OpenAILLMProvider(client=fake_async_openai)` com `await`, mudando apenas:
```python
async def test_invalid_json_raises_provider_error(fake_async_openai):
    fake_async_openai.queue_raw("isto não é json")
    with pytest.raises(ProviderError):
        await OpenAILLMProvider(client=fake_async_openai).complete_json("p")

async def test_api_failure_raises_provider_error(fake_async_openai):
    fake_async_openai.fail_next(openai.APIConnectionError(request=httpx.Request("POST", "http://x")))
    with pytest.raises(ProviderError):
        await OpenAILLMProvider(client=fake_async_openai).complete_text("p")

def test_default_construction_never_reaches_the_network():
    with pytest.raises(AssertionError, match="cliente OpenAI real"):
        OpenAILLMProvider()
```
Mais, para a voz:
```python
async def test_transcribe_sends_portuguese_and_domain_prompt(fake_async_openai):
    fake_async_openai.queue_transcription("eu trabalho à noite")
    text = await OpenAISpeechProvider(client=fake_async_openai).transcribe(b"\x00\x01", "r.webm")
    call = fake_async_openai.last_transcription_call
    assert text == "eu trabalho à noite"
    assert call["model"] == "whisper-1" and call["language"] == "pt" and call["temperature"] == 0
    assert call["file"].name == "r.webm"
    assert call["prompt"] == "Entrevista qualitativa em português sobre o dia a dia de trabalho."

async def test_synthesize_returns_audio_bytes(fake_async_openai):
    fake_async_openai.queue_speech(b"MP3DATA")
    audio = await OpenAISpeechProvider(client=fake_async_openai).synthesize("olá")
    call = fake_async_openai.last_speech_call
    assert audio == b"MP3DATA"
    assert call == {"model": "gpt-4o-mini-tts", "voice": "alloy", "input": "olá"}

@pytest.mark.parametrize("call", ["transcribe", "synthesize"])
async def test_speech_api_failure_raises_provider_error(fake_async_openai, call):
    fake_async_openai.fail_next(openai.APIConnectionError(request=httpx.Request("POST", "http://x")))
    provider = OpenAISpeechProvider(client=fake_async_openai)
    with pytest.raises(ProviderError):
        await (provider.transcribe(b"\x01") if call == "transcribe" else provider.synthesize("olá"))

def test_factory_builds_openai_providers_with_configured_model(monkeypatch, fake_async_openai):
    # o autouse bloqueia AsyncOpenAI; aqui ele é trocado por um construtor que devolve o dublê
    monkeypatch.setattr(openai_provider, "AsyncOpenAI", lambda **kwargs: fake_async_openai)
    s = Settings(llm_provider="openai", llm_model="gpt-4o")
    provider = build_llm_provider(s)
    assert isinstance(provider, OpenAILLMProvider) and provider.model == "gpt-4o"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_providers_fake.py tests/test_openai_provider.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.providers'`

- [ ] **Step 3: Implementar**

- `base.py`: ABCs conforme Interfaces.
- `fake.py`: `complete_json` devolve `dict(FAKE_DECISION)` com `profile_updates` novo (cópia profunda simples).
- `openai_provider.py`: importar `from openai import AsyncOpenAI, OpenAIError` no nível do módulo (o conftest faz monkeypatch de `openai_provider.AsyncOpenAI`). Construtor usa `client or AsyncOpenAI(api_key=settings.openai_api_key or None)`. Expor `model` como atributo público somente leitura (`@property`). Envolver `OpenAIError` e `json.JSONDecodeError` em `ProviderError` (`raise ProviderError(...) from exc`). Transcrição: `io.BytesIO(audio)` com `.name = filename`, `language="pt"`, `temperature=0`, prompt de domínio igual ao `VoiceService` atual. Fala: `await client.audio.speech.create(model=..., voice=..., input=text)` e `return response.content` (no dublê, `content` é atributo bytes).
- `factory.py`: `match settings.llm_provider` → fake ou openai (passando `model=settings.llm_model`).
- `config.py`: os dois campos novos. `.env.example`: `LLM_PROVIDER=openai` e `LLM_MODEL=gpt-4o-mini`.
- `conftest.py`: adicionar `FakeAsyncOpenAI` (métodos async; `queue_raw`, `queue_json`, `queue_transcription`, `queue_speech`, `fail_next(exc)`, `calls`, `last_call`, `last_transcription_call`, `last_speech_call`), fixture `fake_async_openai`, e no autouse `_no_real_openai` também `monkeypatch.setattr(openai_provider, "AsyncOpenAI", _explode)`. Manter por enquanto o patch antigo de `llm_client_module.OpenAI`.

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest -q`
Expected: tudo PASS (suíte antiga intacta + novos)

- [ ] **Step 5: Commit**

```bash
git add app/providers app/core/config.py .env.example tests/conftest.py tests/test_providers_fake.py tests/test_openai_provider.py
git commit -m "feat(EV-41): providers LLM/voz abstratos com implementacoes OpenAI async e fake"
```

---

### Task 2: `DecisionResult` — schema validado da decisão do LLM

**Files:**
- Create: `app/schemas/decision.py`
- Test: `tests/test_decision.py`

**Interfaces:**
- Produces: `class DecisionResult(BaseModel)` com
  `action: Literal["deepen", "advance", "finish"]`, `next_utterance: str = ""`,
  `profile_updates: dict[str, str] = {}`, `closing_statement: str = ""`.
  Campos extras ignorados. Regras de coerção abaixo.

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_parses_a_complete_payload():
    d = DecisionResult.model_validate({"action": "deepen", "next_utterance": "Por quê?",
                                       "profile_updates": {"cargo": "motorista"}, "closing_statement": ""})
    assert d.action == "deepen" and d.profile_updates == {"cargo": "motorista"}

def test_optional_fields_default_to_empty():
    d = DecisionResult.model_validate({"action": "advance"})
    assert (d.next_utterance, d.profile_updates, d.closing_statement) == ("", {}, "")

def test_missing_action_is_invalid():
    with pytest.raises(ValidationError): DecisionResult.model_validate({"next_utterance": "x"})

def test_unknown_action_is_invalid():
    with pytest.raises(ValidationError): DecisionResult.model_validate({"action": "skip"})

def test_null_strings_become_empty():
    d = DecisionResult.model_validate({"action": "finish", "next_utterance": None, "closing_statement": None})
    assert d.next_utterance == "" and d.closing_statement == ""

def test_profile_values_are_coerced_to_strings():
    d = DecisionResult.model_validate({"action": "advance", "profile_updates": {
        "idade": 42, "ativo": True, "turnos": ["manhã", "noite"], "nada": None, "obj": {"a": 1}}})
    assert d.profile_updates == {"idade": "42", "ativo": "true", "turnos": "manhã, noite"}

def test_profile_updates_null_becomes_empty():
    assert DecisionResult.model_validate({"action": "advance", "profile_updates": None}).profile_updates == {}

def test_extra_keys_are_ignored():
    assert DecisionResult.model_validate({"action": "advance", "foo": 1}).action == "advance"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_decision.py -v`
Expected: FAIL com `ModuleNotFoundError`

- [ ] **Step 3: Implementar `DecisionResult` em `app/schemas/decision.py`**

`field_validator(..., mode="before")`: strings `None → ""`; `profile_updates`: `None → {}`; por valor: `bool → "true"/"false"`, `int/float → str`, `str` mantém, `list` de escalares → `", ".join(str(...))`, `None` e `dict` → descartados. `model_config = ConfigDict(extra="ignore")`.

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/test_decision.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/schemas/decision.py tests/test_decision.py
git commit -m "feat(EV-11): schema DecisionResult com coercao do perfil"
```

---

### Task 3: Services async sobre `LLMProvider` (comportamento idêntico)

Migração mecânica: `InterviewService` e `SynthesisService` passam a ser async e a receber `LLMProvider`. Ainda **sem** validação/retry (Task 4) — a lógica de decisão continua igual. Remove `LLMClient`.

**Files:**
- Modify: `app/services/interview_service.py`, `app/services/synthesis_service.py`, `app/api/deps.py`, `app/api/v1/endpoints/session.py`, `app/api/v1/endpoints/turns.py`, `app/main.py`, `tests/conftest.py`, `tests/test_interview_service.py`, `tests/test_synthesis_service.py`, `tests/test_endpoints.py`
- Delete: `app/services/llm_client.py`, `tests/test_llm_client.py`

**Interfaces:**
- Consumes: `LLMProvider`, `ProviderError`, `build_llm_provider` (Task 1).
- Produces:
  - `InterviewService(llm: LLMProvider)` — **obrigatório**, sem default.
  - `async def InterviewService.run_turn(self, interview_state: InterviewState, participant_text: str) -> tuple[InterviewState, str]`
  - `async def InterviewService._decide_node(self, state: GraphState) -> GraphState` — grafo executado com `await self._graph.ainvoke(...)`.
  - `opening_question()` e `finish()` continuam síncronos.
  - `SynthesisService(session_repository: SessionRepository, llm: LLMProvider)` — ambos obrigatórios.
  - `deps.get_llm_provider() -> LLMProvider` (por enquanto `build_llm_provider(settings)` sem cache).
  - Handler em `main.py`: `ProviderError` → `JSONResponse(status_code=502, content={"detail": "Falha ao se comunicar com o provedor de IA."})`.
  - conftest: `FakeLLM(LLMProvider)` com `complete_json`/`complete_text` **async** (mesma API `queue`/`queue_payload`/`prompts`/`last_prompt`), novo `queue_error(exc)` que faz a próxima chamada levantar `exc`; fixture `service` → `InterviewService(llm=fake_llm)`.

- [ ] **Step 1: Atualizar os testes para a nova API (eles passam a falhar)**

- `test_interview_service.py`: `pytestmark = pytest.mark.anyio`; todo `service.run_turn(...)` e `service._decide_node(...)` vira `await`; testes de `TestDecideNode`/`run_turn` viram `async def`; `InterviewService(llm_client=...)` → `InterviewService(llm=...)`; asserção `._llm is fake_llm` mantida.
- `test_synthesis_service.py`: `SynthesisService(session_repository=repository, llm=fake_llm)`; remover `test_builds_a_default_repository` e `test_default_construction_never_reaches_the_network` (sem defaults agora); adicionar:
```python
async def test_provider_error_propagates(synthesis, repository, fake_llm, finished_state):
    await repository.create(finished_state)
    fake_llm.queue_error(ProviderError("fora do ar"))
    with pytest.raises(ProviderError):
        await synthesis.synthesize(finished_state.session_id)
```
- `test_endpoints.py`: overrides com `llm=fake_llm`; adicionar:
```python
def test_synthesis_when_provider_fails_returns_502(client, fake_llm):
    session_id = _abrir_sessao(client)
    client.post(f"/session/{session_id}/finish")
    fake_llm.queue_error(ProviderError("timeout"))
    response = client.post(f"/session/{session_id}/synthesis")
    assert response.status_code == 502
    assert response.json() == {"detail": "Falha ao se comunicar com o provedor de IA."}
```
- Apagar `tests/test_llm_client.py` (casos já portados na Task 1).

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest -q`
Expected: FAIL (`TypeError` em `InterviewService(llm=...)`, coroutines não aguardadas)

- [ ] **Step 3: Implementar**

Services async conforme Interfaces; endpoints com `await interview.run_turn(...)` e `await synthesis.synthesize(...)`; `deps.get_interview_service()` → `InterviewService(llm=get_llm_provider())`, `get_synthesis_service()` → `SynthesisService(get_session_repository(), get_llm_provider())`; handler 502 em `main.py`; apagar `llm_client.py` e o patch de `llm_client_module` no conftest.

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest -q`
Expected: PASS, cobertura ≥ 70%

- [ ] **Step 5: Commit**

```bash
git add -A app tests
git commit -m "refactor(EV-10): services async sobre LLMProvider e erro de provedor vira 502"
```

---

### Task 4: Decisão validada com retry e fallback

**Files:**
- Modify: `app/services/interview_service.py`
- Test: `tests/test_interview_service.py`

**Interfaces:**
- Consumes: `DecisionResult` (Task 2), `ProviderError` (Task 1), `FakeLLM.queue_error` (Task 3).
- Produces:
  - `MAX_DECISION_ATTEMPTS = 2` (1 tentativa + 1 retry) em `interview_service.py`.
  - `FALLBACK_DECISION = DecisionResult(action="advance")`.
  - `async def InterviewService._request_decision(self, prompt: str) -> DecisionResult` — chama `complete_json`, valida; em `ProviderError` ou `ValidationError` tenta de novo até `MAX_DECISION_ATTEMPTS`; esgotou → `logger.warning(...)` e devolve `FALLBACK_DECISION`.
  - `_decide_node` passa a usar `_request_decision` e campos tipados (`decision.action`, `decision.profile_updates`, ...). Regra existente "finish antes da última pergunta → advance" mantida.

- [ ] **Step 1: Escrever os testes que falham** (classe `TestDecisionValidation`)

```python
async def test_invalid_payload_is_retried_once(service, fake_llm, state):
    fake_llm.queue_payload({"next_utterance": "sem action"})
    fake_llm.queue(action="deepen", next_utterance="Me conta mais?")
    _, fala = await service.run_turn(state, "resposta")
    assert fala == "Me conta mais?" and len(fake_llm.prompts) == 2

async def test_unknown_action_falls_back_to_advance_after_retries(service, fake_llm, state):
    fake_llm.queue_payload({"action": "skip"}).queue_payload({"action": "skip"})
    _, fala = await service.run_turn(state, "resposta")
    assert state.current_index == 1 and fala == CORE_QUESTIONS[1]
    assert len(fake_llm.prompts) == MAX_DECISION_ATTEMPTS

async def test_provider_error_falls_back_to_advance(service, fake_llm, state):
    fake_llm.queue_error(ProviderError("timeout")).queue_error(ProviderError("timeout"))
    _, fala = await service.run_turn(state, "resposta")
    assert fala == CORE_QUESTIONS[1] and not state.finished

async def test_provider_error_then_success_uses_the_success(service, fake_llm, state):
    fake_llm.queue_error(ProviderError("timeout")).queue(action="deepen", next_utterance="E aí?")
    _, fala = await service.run_turn(state, "resposta")
    assert fala == "E aí?" and state.current_index == 0

async def test_fallback_on_the_last_question_finishes(service, fake_llm, state):
    state.current_index = LAST_INDEX
    fake_llm.queue_payload({}).queue_payload({})
    _, fala = await service.run_turn(state, "resposta")
    assert state.finished and fala == DEFAULT_CLOSING

async def test_non_string_profile_values_survive_a_repository_round_trip(service, fake_llm, state, fake_db):
    repo = SessionRepository(database=fake_db)
    await repo.create(state)
    fake_llm.queue(action="deepen", next_utterance="?", profile_updates={"idade": 42, "turnos": ["manhã"], "x": None})
    await service.run_turn(state, "resposta"); await repo.save(state)
    reloaded = await repo.get(state.session_id)
    assert reloaded.profile == {"idade": "42", "turnos": "manhã"}
```
Atualizar `test_tolerates_response_without_optional_keys` se depender de chaves cruas (deve continuar passando).

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_interview_service.py -v -k "DecisionValidation"`
Expected: FAIL (`KeyError: 'action'`, `ImportError: MAX_DECISION_ATTEMPTS`)

- [ ] **Step 3: Implementar `_request_decision` e adaptar `_decide_node`** conforme Interfaces (`logger = logging.getLogger(__name__)`).

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/interview_service.py tests/test_interview_service.py
git commit -m "feat(EV-11): decisao do LLM validada com retry e fallback deterministico"
```

---

### Task 5: Endpoints de voz sobre `SpeechProvider` + voz na cobertura

**Files:**
- Modify: `app/api/v1/endpoints/voice.py`, `app/api/deps.py`, `pyproject.toml`
- Delete: `app/services/voice_service.py`
- Test: `tests/test_voice_endpoints.py`

**Interfaces:**
- Consumes: `SpeechProvider`, `build_speech_provider`, `FakeSpeechProvider` (Task 1); handler 502 (Task 3).
- Produces: `deps.get_speech_provider() -> SpeechProvider` (sem cache ainda); `get_voice_service` removido. Rotas `/voice/transcricao` e `/voice/fala` com o mesmo contrato.

- [ ] **Step 1: Escrever os testes que falham**

Fixture `client` com `app.dependency_overrides[get_speech_provider] = lambda: speech` onde `speech` é um dublê `RecordingSpeech(SpeechProvider)` que grava chamadas e pode ser configurado para levantar `ProviderError`.
```python
def test_transcription_returns_the_text(client, speech):
    r = client.post("/voice/transcricao", files={"file": ("r.webm", b"\x01\x02", "audio/webm")})
    assert r.status_code == 200 and r.json() == {"texto": speech.transcription}
    assert speech.transcribe_calls == [(b"\x01\x02", "r.webm")]

def test_empty_audio_returns_400_without_calling_the_provider(client, speech):
    r = client.post("/voice/transcricao", files={"file": ("r.webm", b"", "audio/webm")})
    assert r.status_code == 400 and r.json() == {"detail": "Áudio vazio."}
    assert speech.transcribe_calls == []

def test_speech_returns_mpeg_audio(client, speech):
    r = client.post("/voice/fala", json={"texto": "olá"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
    assert r.content == speech.audio

def test_speech_rejects_empty_text(client):
    assert client.post("/voice/fala", json={"texto": ""}).status_code == 422

def test_provider_failure_returns_502(client, speech):
    speech.fail_with(ProviderError("fora"))
    r = client.post("/voice/fala", json={"texto": "olá"})
    assert r.status_code == 502
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_voice_endpoints.py -v`
Expected: FAIL (`ImportError: get_speech_provider`)

- [ ] **Step 3: Implementar**

Endpoints `await speech.transcribe(...)` / `await speech.synthesize(...)`; áudio vazio → `raise HTTPException(400, "Áudio vazio.")`; apagar `voice_service.py`; remover o bloco `omit` de `[tool.coverage.run]` no `pyproject.toml`.

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest -q --cov-fail-under=70`
Expected: PASS, cobertura ≥ 70% incluindo `voice.py`

- [ ] **Step 5: Commit**

```bash
git add -A app pyproject.toml tests
git commit -m "feat(EV-41): voz sobre SpeechProvider, audio vazio vira 400 e voz entra na cobertura"
```

---

### Task 6: Dependências como singletons

**Files:**
- Modify: `app/api/deps.py`
- Test: `tests/test_deps.py`

**Interfaces:**
- Consumes: factories (Task 1), services (Tasks 3–5).
- Produces: `get_llm_provider`, `get_speech_provider`, `get_session_repository`, `get_interview_service`, `get_synthesis_service` decorados com `@lru_cache(maxsize=1)`; função `reset_dependencies() -> None` que chama `cache_clear()` em todas (usada por testes).

- [ ] **Step 1: Escrever os testes que falham**

Fixture autouse no arquivo: `monkeypatch.setattr(deps.settings, "llm_provider", "fake")` + `reset_dependencies()` antes e depois.
```python
def test_providers_follow_the_configured_backend():
    assert isinstance(deps.get_llm_provider(), FakeLLMProvider)
    assert isinstance(deps.get_speech_provider(), FakeSpeechProvider)

def test_interview_service_is_a_singleton():
    assert deps.get_interview_service() is deps.get_interview_service()

def test_services_share_the_same_llm_provider():
    assert deps.get_interview_service()._llm is deps.get_synthesis_service()._llm is deps.get_llm_provider()

def test_reset_dependencies_rebuilds_instances():
    first = deps.get_interview_service(); deps.reset_dependencies()
    assert deps.get_interview_service() is not first

def test_graph_is_compiled_once():
    assert deps.get_interview_service()._graph is deps.get_interview_service()._graph

def test_full_interview_runs_offline_with_fake_providers():
    # só o repositório é sobrescrito; InterviewService real, montado pelo deps com FakeLLMProvider
    repo = SessionRepository(database=FakeDB())
    app.dependency_overrides[deps.get_session_repository] = lambda: repo
    try:
        with TestClient(app) as client:
            session_id = client.post("/session").json()["session_id"]
            replies = [client.post(f"/turn/{session_id}", json={"texto": "resposta"}).json()
                       for _ in CORE_QUESTIONS]
    finally:
        app.dependency_overrides.clear()
    assert [r["finalizada"] for r in replies] == [False, False, False, True]
    assert replies[-1]["fala"] == DEFAULT_CLOSING
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_deps.py -v`
Expected: FAIL (`AttributeError: reset_dependencies`, instâncias diferentes)

- [ ] **Step 3: Implementar** os decorators e `reset_dependencies()` em `deps.py`.

- [ ] **Step 4: Rodar a suíte inteira com cobertura**

Run: `pytest -q --cov-fail-under=70`
Expected: PASS; `tests/test_endpoints.py` continua passando (overrides funcionam com funções cacheadas).

- [ ] **Step 5: Commit**

```bash
git add app/api/deps.py tests/test_deps.py
git commit -m "feat(EV-12): dependencias como singletons com reset para testes"
```

---

### Task 7: Fechamento — spec e smoke test

**Files:**
- Modify: `docs/EVOLUCOES.md` (status de EV-10, EV-11, EV-12, EV-41 → `DONE`; RK-03 e RK-07 com nota "mitigado")

- [ ] **Step 1: Smoke test offline**

Run: `LLM_PROVIDER=fake uvicorn app.main:app --port 8001` (em background) e `curl -s -X POST localhost:8001/session`
Expected: JSON com `session_id` e `pergunta` igual a `CORE_QUESTIONS[0]`. Mongo local necessário; se não houver, pular e registrar.

- [ ] **Step 2: Atualizar a spec e commitar**

```bash
git add docs/EVOLUCOES.md
git commit -m "docs: marca EV-10, EV-11, EV-12 e EV-41 como concluidos"
```
