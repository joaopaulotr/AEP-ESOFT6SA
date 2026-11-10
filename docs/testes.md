# Testes, cobertura e entrega

Como rodar cada suíte, o que ela cobre, os números atuais e como a entrega é verificada.
Os comandos abaixo foram executados neste repositório. Instalação e variáveis de ambiente:
[README](../README.md#5-como-executar).

## 1. Suítes

| Suíte | Onde | Banco | Quantidade | O que cobre |
|---|---|---|---|---|
| **Unitários e de API** (pytest) | `backend/tests/` | MongoDB simulado em memória (`mongomock-motor`) | 676 | Modelos, repositórios, serviços, endpoints, grafo de decisão, segurança, providers, importação, síntese, SSE, métricas e logs |
| **Integração com Mongo real** (`-m mongo`) | `backend/tests/test_mongo_integration.py` | MongoDB de verdade (`MONGO_TEST_URI`) | 12 | Índices e unicidade no servidor, `$lookup`, agregações do painel, controle de `versao`, migração v0.1.0, exclusão do relatório do roteiro que usou a sessão apagada |
| **E2E** (Playwright) | `frontend/e2e/` | MongoDB real, banco `aep_e2e` | 9 testes em 6 arquivos | Fluxos completos no navegador, com a API real e `LLM_PROVIDER=fake` |

### 1.1 Unitários e de API

Rodam sem rede, sem OpenAI e sem MongoDB instalado: o provider é um dublê ou o `fake`, e o
banco é o `mongomock-motor` (executa filtros, índices únicos e pipelines de agregação). O
`conftest.py` monta o app com esse banco.

Principais arquivos, por área:

- **Repositórios e modelos:** `test_base_repository.py`, `test_script_repository.py`,
  `test_session_repository.py`, `test_synthesis_repository.py`, `test_schemas_colecoes.py`,
  `test_dashboard.py`.
- **Serviços:** `test_interview_service.py`, `test_interview_graph.py`, `test_decision.py`,
  `test_safety.py`, `test_session_service.py`, `test_script_service.py`,
  `test_synthesis_service.py`, `test_synthesis_structured.py`, `test_script_synthesis.py`,
  `test_import_service.py`, `test_import_extractors.py`.
- **Endpoints:** `test_endpoints.py`, `test_scripts_api.py`, `test_participants_api.py`,
  `test_sessions_api.py`, `test_invites_api.py`, `test_import_api.py`, `test_turn_stream.py`,
  `test_voice_endpoints.py`.
- **Providers e infraestrutura:** `test_openai_provider.py` (cliente OpenAI simulado),
  `test_providers_fake.py`, `test_usage.py`, `test_logging.py`, `test_deps.py`,
  `test_demo_seed.py`.

Os casos negativos com código HTTP (404, 409, 411, 413, 415, 422 em pt-BR, 502) ficam aqui, no
pytest, e não no E2E; o E2E cobre só os negativos que o participante vê na tela.

### 1.2 Integração com MongoDB real

Marcados com `@pytest.mark.mongo` (`--strict-markers`, declarado em `pyproject.toml`). Sem
`MONGO_TEST_URI` eles são **pulados** (são os 12 "skipped" da execução padrão). Cada teste cria
um banco temporário `aep_it_<id>` e o apaga ao final.

### 1.3 E2E (Playwright)

Nove testes, na ordem dos arquivos:

| Arquivo | Cenário |
|---|---|
| `01-pesquisador.spec.js` | Pesquisador: roteiros do seed, entrevistas concluídas, transcrição e síntese com citação |
| `02-importacao.spec.js` | Importação: subir questionário, revisar no editor, publicar e ver na lista |
| `03-convite-texto.spec.js` | Convite e modo texto: responde tudo, agradecimento, entrevista concluída e síntese |
| `04-painel.spec.js` | Painel: cartões, gráficos, tabela de dados e relatório do roteiro |
| `05-negativos.spec.js` | Convite inexistente mostra "convite encerrado"; pedido de parar no modo texto encerra com a mensagem de parada; sofrimento no modo texto mantém o cartão do CVV até "Continuar" e o repete no agradecimento |
| `06-voz.spec.js` | Voz, ciclo completo: grava, clica "Parar e enviar", confirma o que foi entendido e espera a próxima pergunta (o teste falha se houver erro de console); microfone negado mostra o aviso e deixa passar para o modo escrever |

Como é montado (`frontend/playwright.config.js`, `frontend/e2e/global-setup.js`):

- O Python do backend é resolvido por `frontend/e2e/ambiente.js` (módulo único, usado pela config e pelo
  `global-setup.js`): `E2E_PYTHON`, senão `backend/.venv/Scripts/python` (Windows) ou
  `backend/.venv/bin/python` (Linux/macOS), senão o do `PATH`, sempre relativo ao próprio arquivo (não ao cwd).
- Os servidores usam `reuseExistingServer: false`: o E2E nunca reaproveita um backend ou Vite já aberto
  (que poderia apontar para outro banco); se a porta estiver ocupada, falha.
- O Playwright sobe o backend (`uvicorn` na porta 8090) com `LLM_PROVIDER=fake`, banco
  `aep_e2e` e `OPENAI_API_KEY=test-key`, e o Vite na porta 5190 com `VITE_E2E=1`. **Nunca usa a
  OpenAI nem o banco de desenvolvimento.**
- Antes de cada execução, `global-setup.js` esvazia as coleções de `aep_e2e` (com
  `assert db.name == "aep_e2e"`) e roda `python -m scripts.seed_demo --reset`: cada execução
  começa do mesmo estado.
- `VITE_E2E=1` (`src/utils/e2e.js`) zera os atrasos de realismo (tempo de "pensar", digitação
  letra a letra, fillers de voz, incentivo por silêncio). Os testes esperam pelo estado da
  tela, nunca por tempo fixo. Em produção a variável não existe.
- `workers: 1` (banco compartilhado), ordem por nome de arquivo, `retries: 1` só no CI.
- Microfone falso do Chromium: `--use-fake-ui-for-media-stream
  --use-fake-device-for-media-stream`.
- Detalhes e cuidados (portas 8090/5190 livres, `E2E_MONGO_URI`, `E2E_PYTHON`):
  `frontend/e2e/README.md`.

## 2. Como rodar

Pré-requisito comum: dependências instaladas (`cd backend && python -m venv .venv` e `pip install
-r requirements-dev.txt`; `cd frontend && npm install`). Os exemplos usam o caminho do venv do
Linux/macOS (`.venv/bin`); no Windows troque por `.venv/Scripts`.

### Unitários (com cobertura)

```bash
cd backend && .venv/bin/python -m pytest            # Windows: .venv/Scripts/python
cd backend && .venv/bin/python -m pytest --cov-fail-under=70    # com o mínimo da CI
cd backend && .venv/bin/python -m pytest --cov-report=html      # relatório em backend/htmlcov/
```

A cobertura (`pytest-cov`, com `branch = true` e `source = ["app"]`) já vem ligada em
`addopts` de `pyproject.toml`. Sem chave real: o teste não chama a OpenAI.

### Integração (`-m mongo`)

```bash
docker compose up -d mongo
cd backend && MONGO_TEST_URI=mongodb://localhost:27017 .venv/bin/python -m pytest -m mongo --no-cov
```

No PowerShell:

```powershell
docker compose up -d mongo
cd backend
$env:MONGO_TEST_URI = "mongodb://localhost:27017"
.venv/Scripts/python -m pytest -m mongo --no-cov
```

### E2E

Requer um MongoDB em `127.0.0.1:27017` (ou `E2E_MONGO_URI`) e o venv do backend (ou
`E2E_PYTHON`). Pare servidores de desenvolvimento nas portas 8090 e 5190 antes.

```bash
docker compose up -d mongo
cd frontend && npx playwright install chromium     # só na primeira vez
cd frontend && npx playwright test
```

O mesmo comando funciona no Windows (PowerShell). O relatório HTML fica em
`frontend/playwright-report/`.

### Lint e build do frontend

```bash
cd frontend && npm run lint && npm test && npm run build
```

- O lint roda com `--max-warnings=0`: **aviso também falha** (não só erro).
- `npm test` roda os testes unitários do frontend (Vitest, 27 testes em 3 arquivos: funções puras
  como `atrasoDePensar`, `pausaApos`, `sortear`, `lerEventosSSE` e os textos), sem rede nem navegador.

## 3. `scripts/verify-delivery.sh`

Verificação determinística da entrega (precisa de Git Bash no Windows):

```bash
bash scripts/verify-delivery.sh                 # higiene + backend + frontend (padrão)
bash scripts/verify-delivery.sh --backend       # pytest com cobertura >= 70% e checagem de omit
bash scripts/verify-delivery.sh --frontend      # npm ci, lint (se houver) e build
bash scripts/verify-delivery.sh --integration   # pytest -m mongo (exige MONGO_TEST_URI)
bash scripts/verify-delivery.sh --e2e           # Playwright (exige frontend/playwright.config.js)
```

O que cada passo faz (no código do script):

- **Higiene** (só no modo padrão): falha se estiver versionado um `.env`, `.coverage`,
  `.reviews/` ou `.superpowers/`.
- **Backend:** `pytest -q --cov-fail-under=70` (usa `OPENAI_API_KEY=test-key` se não houver
  chave) e falha se `backend/pyproject.toml` tiver `omit` na cobertura: o código é testado, não
  excluído da medição.
- **Frontend:** `npm ci`, `npm run lint` (0 avisos), `npm test` (Vitest) e `npm run build`.
- **`--integration` e `--e2e`** não entram no modo padrão: precisam de MongoDB.

Termina com `[OK] verificação concluída (<modo>)` ou `[FALHOU] <motivo>` (código de saída 1).

## 4. CI (GitHub Actions)

| Workflow | Quando roda | Job | O que faz |
|---|---|---|---|
| `.github/workflows/backend-ci.yml` | push e PR que mudam `backend/**` | `unit` | Python 3.11, `pip install -r requirements-dev.txt`, `pytest --cov-fail-under=70` com relatórios `term-missing`, `xml` e `html`; escreve `coverage report` no resumo do job (`$GITHUB_STEP_SUMMARY`) e publica `backend/htmlcov` e `backend/coverage.xml` como artefato `cobertura` |
| | | `integration` | Service container `mongo:7` com healthcheck; `pytest -m mongo --no-cov` com `MONGO_TEST_URI=mongodb://localhost:27017/ci` |
| `.github/workflows/frontend-ci.yml` | push e PR que mudam `frontend/**` ou `backend/**` | `lint-build` | Node 20, `npm ci`, `npm run lint` (0 avisos), `npm test` (Vitest), `npm run build` |
| | | `e2e` (depende de `lint-build`) | Service container `mongo:7`; instala o backend (`pip install -r backend/requirements.txt`), o Chromium do Playwright e roda `npx playwright test`; em falha, publica `playwright-report/` e `test-results/` como artefato (7 dias) |

Nenhum job exige segredos: o CI usa `OPENAI_API_KEY=test-key` e o provider `fake` no E2E. Cada
job falha de verdade se a cobertura ficar abaixo de 70%, o lint ou o build falharem, ou um
teste (unitário, de integração ou E2E) quebrar.

## 5. Cobertura

- **Mínimo exigido: 70%** (`--cov-fail-under=70`, na CI e em `verify-delivery.sh`), com medição de
  branches e sem nenhum `omit`: a camada de voz e os providers entram na cobertura.
- **Número atual** (`bash scripts/verify-delivery.sh --backend`): **98,5%** (2.505
  instruções, 19 sem cobertura; 432 branches, 26 parciais) com **676 testes passando e 12
  pulados** (os de integração), em cerca de 1 minuto.
- **Evidência:** o relatório HTML e o `coverage.xml` não ficam no repositório (`backend/htmlcov/` e
  `coverage.xml` estão no `.gitignore`); são gerados a cada execução da CI e publicados como
  artefato `cobertura`, com a tabela por arquivo no resumo do job. Localmente:
  `pytest --cov-report=html` gera `backend/htmlcov/index.html`.

## 6. Processo de entrega

Toda entrega segue a rotina `/entregar` (`.claude/skills/entregar/SKILL.md`):

1. **Branch e commits** por item da spec (Conventional Commits em português).
2. **Verificação determinística:** `bash scripts/verify-delivery.sh`.
3. **Três revisões independentes por agentes** (`.claude/agents/`): `revisor-spec` (aderência à
   spec `docs/EVOLUCOES.md` e à AEP), `revisor-codigo` (backend, providers, Mongo, testes) e
   `revisor-interface` (frontend, quando a mudança o toca). Os achados P1 e P2 são corrigidos
   com teste; P3 se for barato, senão vira limite no PR.
4. **Spec atualizada:** `docs/EVOLUCOES.md` marca os itens como concluídos e registra decisões e
   riscos.
5. **PR** com a verificação em números e os limites que seguem abertos.
