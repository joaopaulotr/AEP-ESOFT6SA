# Banco multi-coleção e repositórios por agregado — Plano de implementação

**Objetivo:** cumprir o requisito NoSQL do 2º semestre da AEP (R2: múltiplas coleções, relacionamento
entre coleções e objetos complexos) e reforçar POO (R3) com repositórios genéricos, **sem mudar o
contrato HTTP** usado pelo frontend.

**Spec:** `docs/EVOLUCOES.md`, itens **EV-01** (modelagem multi-coleção) e **EV-02** (repositórios por
agregado + base genérica). EV-03 (rotas CRUD das coleções novas) fica para a próxima entrega e
consome o que este plano cria.

**Branch:** `feat/EV-01-multi-colecao` a partir da `main` (`d519261`).

---

## 1. O que a AEP pede e como este plano atende

| Exigência (2º semestre) | Como fica |
|---|---|
| Múltiplas coleções | `interview_scripts`, `participants`, `interview_sessions`, `syntheses` |
| Relacionamento entre coleções | `interview_sessions.script_id → interview_scripts`, `interview_sessions.participant_id → participants`, `syntheses.session_id → interview_sessions`, `syntheses.script_id → interview_scripts`. Consulta com `$lookup` (sessão + roteiro + participante) |
| Objetos complexos | `interview_scripts.perguntas[]`, `.origem{}`, `.persona{}`; `interview_sessions.conversation[]`, `.profile{}`, `.metricas{}`; `syntheses.temas[].citacoes[]` |
| Uso efetivo (não só modelagem) | Índices únicos criados no `lifespan`, roteiro *seed* lido do banco a cada entrevista, `max_aprofundamentos` da pergunta aplicado no turno, síntese gravada em `syntheses`, pipelines de agregação para o dashboard (EV-32) |
| Evidência reproduzível | Testes unitários com `mongomock-motor` (CI sem Mongo) **e** testes de integração contra MongoDB real (`-m mongo`), que rodam no CI com um container `mongo:7` |

## 2. Decisões

| # | Decisão | Motivo |
|---|---|---|
| D1 | `CORE_QUESTIONS` vira o roteiro *seed* `entrevista-generalista` (slug `generalista`), inserido com `upsert` no startup. `POST /session` sem corpo usa esse roteiro. | Contrato HTTP intacto; o roteiro deixa de ser constante e passa a ser dado. |
| D2 | `InterviewState.script_id` tem default `entrevista-generalista`. | Sessões antigas (v0.1.0, sem `script_id`) continuam carregando e apontam para o roteiro equivalente ao que usaram. |
| D3 | `status` (`em_andamento`/`concluida`) é campo calculado a partir de `finished` e é gravado no documento. | A spec pede `status`; derivar evita duas fontes de verdade e o campo fica disponível para `$match`/`$group`. |
| D4 | A síntese sai de `interview_sessions.synthesis` e vai para `syntheses` (`escopo: sessao`), uma por sessão (regerar substitui). | Uma fonte de verdade; prepara EV-13 (cache) e EV-33 (síntese por roteiro). O campo antigo é ignorado na leitura. |
| D5 | Turnos ganham `pergunta_ordem`, `acao` e `latencia_ms`. `acao` só nas falas do entrevistador (abertura = `null`). | Alimenta os pipelines do dashboard e o limite de aprofundamentos. |
| D6 | `max_aprofundamentos` é aplicado: `deepen` além do limite da pergunta vira `advance`. | Sem isso o campo seria dado morto; também evita prender o participante numa pergunta. |
| D7 | `SessionService` orquestra abrir/turno/encerrar (repositórios + `InterviewService`). Rotas só traduzem. Erros de domínio `NotFoundError` → 404 e `ConflictError` → 409 em `main.py`. | Com o roteiro vindo do banco, a lógica deixaria de caber na rota (R3: camadas). |
| D8 | `BaseRepository[T]` genérico com `create/get/get_or_raise/save/delete/list/count/ensure_indexes`; `DuplicateKeyError` vira `ConflictError`. `delete` devolve `bool` em vez de `ValueError` (que virava 400). | Herança e genéricos aplicados de fato; quem chama decide o 404. |
| D9 | O banco é injetado (`deps.get_database()`); nenhum repositório lê global escondido. Cliente Motor com `tz_aware=True`. | DI explícita; datas voltam do Mongo com fuso, iguais às criadas em Python. |
| D10 | Testes trocam o `FakeDB` caseiro por `mongomock-motor` (dependência só de dev). | O dublê antigo não executa `aggregate`, índices nem filtros; o mock executa pipelines de verdade. |

## 3. Estrutura de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `app/core/errors.py` | Criar | `DomainError`, `NotFoundError`, `ConflictError` |
| `app/schemas/script.py` | Criar | `InterviewScript`, `Question`, `ScriptOrigin`, `Persona`, `slugify` |
| `app/schemas/participant.py` | Criar | `Participant` |
| `app/schemas/synthesis.py` | Criar | `Synthesis`, `Theme`, `Citation` |
| `app/schemas/interview.py` | Alterar | `Turn` (+`pergunta_ordem`, `acao`, `latencia_ms`), `InterviewState` (+`script_id`, `participant_id`, `status`, `metricas`; −`synthesis`), `SessionMetrics`, `SessionDetails`, `ScriptStats` |
| `app/db/mongodb.py` | Alterar | cliente com `tz_aware=True` |
| `app/db/seed.py` | Criar | roteiro *seed* (`CORE_QUESTIONS`, `SEED_SCRIPT_ID`, `generalist_script()`) |
| `app/repositories/base.py` | Criar | `BaseRepository[T]` |
| `app/repositories/script_repository.py` | Criar | `get_by_slug`, `list_active`, `ensure_seed`, `get_default` |
| `app/repositories/participant_repository.py` | Criar | índice e CRUD herdado |
| `app/repositories/session_repository.py` | Reescrever | herda a base; `list_by_script`, `list_by_participant`, `get_details` (`$lookup`), `script_stats` (aggregation) |
| `app/repositories/synthesis_repository.py` | Criar | `get_for_session`, `list_for_script`, `save_for_session` |
| `app/services/interview_service.py` | Alterar | recebe o `InterviewScript`; anota turnos; aplica `max_aprofundamentos` |
| `app/services/session_service.py` | Criar | orquestra sessão (D7) |
| `app/services/synthesis_service.py` | Alterar | grava em `syntheses` |
| `app/api/deps.py` | Alterar | banco, 4 repositórios, `SessionService` |
| `app/api/v1/endpoints/session.py`, `turns.py` | Alterar | usam `SessionService` |
| `app/main.py` | Alterar | `lifespan` (índices + seed) e handlers de domínio |
| `requirements-dev.txt`, `pyproject.toml` | Alterar | `mongomock-motor`; marcador `mongo` |
| `.github/workflows/backend-ci.yml` | Alterar | serviço `mongo:7` + `MONGO_TEST_URI` |
| `tests/…` | Criar/alterar | ver tarefa 6 |
| `README.md`, `docs/EVOLUCOES.md` | Alterar | modelo de dados novo; EV-01/EV-02 `DONE`, RK-01 |

## 4. Tarefas

### Tarefa 1 — Esquemas (EV-01)
- [x] `Question(ordem ≥ 1, texto não vazio, objetivo, max_aprofundamentos 0..5 = 2)`.
- [x] `InterviewScript`: `perguntas` com pelo menos 1 item, ordenadas por `ordem`, sem `ordem` repetida;
      `slug_convite` gerado do título quando vazio; `origem{tipo: manual|upload, arquivo?, extraido_em?}`;
      `persona{nome, tom: acolhedor|neutro|formal}`; `ativo`; datas.
- [x] `Participant(participant_id, apelido?, faixa_etaria?, regiao?, canal: voz|texto)`.
- [x] `Synthesis(escopo: sessao|roteiro)`: `sessao` exige `session_id`; `roteiro` não aceita `session_id`.
- [x] `InterviewState`/`Turn` conforme D2, D3, D5.

### Tarefa 2 — Base genérica e repositórios (EV-02)
- [x] `BaseRepository[T]` (D8); conversão documento ⇄ modelo num só lugar (remove `_id`).
- [x] Índices: `script_id`↑ único, `slug_convite`↑ único, `ativo`; `participant_id` único;
      `session_id` único, `script_id`, `participant_id`; `synthesis_id` único, `session_id`, `script_id`.
- [x] `SessionRepository.get_details`: `$match` → `$lookup` roteiro → `$lookup` participante → `$unwind`
      (participante opcional) → `$project` sem `_id`.
- [x] `SessionRepository.script_stats`: total, concluídas, taxa de conclusão, média de respostas do
      participante, distribuição de ações (`$unwind` + `$group`) e média de aprofundamentos por pergunta.

### Tarefa 3 — Roteiro vindo do banco (EV-01)
- [x] `app/db/seed.py` e `ScriptRepository.ensure_seed()` (idempotente).
- [x] `InterviewService.opening_question(script)` e `run_turn(state, script, texto)`; prompt com
      perguntas restantes numeradas (em vez do `repr` de lista) e objetivo da pergunta atual.

### Tarefa 4 — `SessionService` e síntese
- [x] `start(script_id=None, participant_id=None)`: roteiro inexistente → 404, inativo → 409,
      participante inexistente → 404.
- [x] `take_turn`: sessão inexistente → 404, encerrada → 409, roteiro apagado → 404.
- [x] `SynthesisService` grava em `syntheses` (D4) e continua devolvendo o texto.

### Tarefa 5 — Injeção e startup
- [x] `deps.get_database()` + getters dos 4 repositórios + `get_session_service`; `reset_dependencies`.
- [x] `lifespan`: `ensure_indexes()` de todos os repositórios e `ensure_seed()`.

### Tarefa 6 — Testes
- [x] `conftest`: `fake_db` com `mongomock-motor`; fixture autouse aponta `deps` para o banco em memória.
- [x] Unitários: esquemas, base genérica, cada repositório, `$lookup`, estatísticas, seed, `SessionService`,
      limite de aprofundamentos, síntese em `syntheses`, compatibilidade com documento da v0.1.0.
- [x] Integração (`-m mongo`, `MONGO_TEST_URI`): índices únicos, `$lookup` e agregação no MongoDB real.
- [x] Endpoints: contrato inalterado (mesmos campos e códigos).

### Tarefa 7 — Documentação e spec
- [x] README: seção "Modelo de dados" com as 4 coleções, relacionamentos e índices; comando dos testes de integração.
- [x] `docs/EVOLUCOES.md`: EV-01 e EV-02 `DONE` com as decisões; RK-01 parcialmente mitigado (falta EV-03).

## 5. Verificação

```bash
bash scripts/verify-delivery.sh --backend                            # pytest + cobertura ≥ 70%, sem omit
cd backend && MONGO_TEST_URI=mongodb://localhost:27017 pytest -m mongo   # integração com Mongo real
```

## 6. Fora deste plano

- Rotas `/scripts`, `/participants`, `/sessions/{id}/detalhes`, `/syntheses` (EV-03).
- Upload de questionário (EV-30), persona no prompt (EV-21), métricas preenchidas (EV-62),
  síntese estruturada e por roteiro (EV-33), cache da síntese (EV-13).
