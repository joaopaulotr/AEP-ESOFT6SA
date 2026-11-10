# Fase 5 — Qualidade e evidência: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Evidência reproduzível para a banca: testes E2E dos fluxos principais, CI do backend e do frontend (lint, build, testes, cobertura publicada, integração com Mongo real) e documentação técnica completa (arquitetura, banco, API, testes).

**Architecture:** Playwright em `frontend/e2e` sobe backend (`LLM_PROVIDER=fake`, Mongo real de teste) e Vite; CI com jobs separados (backend unit+cobertura, backend integração com `mongo:7`, frontend lint+build, E2E). Cobertura sai do repositório e vira artefato + resumo no job. Docs técnicas em `docs/`.

**Tech Stack:** Playwright (`@playwright/test`), ESLint 9 flat config (`eslint`, `@eslint/js`, `eslint-plugin-react`, `eslint-plugin-react-hooks`, `globals`), GitHub Actions, pytest-cov.

**Spec:** `docs/EVOLUCOES.md` — EV-05, EV-06, EV-70, EV-72; riscos RK-03, RK-04; resíduos das fases anteriores (teste de painel no Mongo real; testes de front).

## Global Constraints

- Dependências novas **só de desenvolvimento** no front: `@playwright/test`, `eslint`, `@eslint/js`, `eslint-plugin-react`, `eslint-plugin-react-hooks`, `globals`. Backend: nenhuma.
- E2E nunca usa OpenAI (`LLM_PROVIDER=fake`) nem o banco de desenvolvimento (banco `aep_e2e`, limpo antes de cada execução).
- CI não pode exigir segredos (sem `OPENAI_API_KEY` real).
- `bash scripts/verify-delivery.sh` continua passando e ganha `--e2e`.
- Nada de afrouxar critério para ficar verde (cobertura ≥ 70%, sem `omit`, lint sem `--max-warnings` alto).
- Docs em pt-BR, conferidas contra o código (nada inventado); diagramas mermaid válidos.

## Review Focus

1. E2E dependente de tempo (digitação/atrasos do modo texto) → os testes esperam por estado da UI, nunca `waitForTimeout` fixo; atrasos de realismo podem ser reduzidos por flag de ambiente só para E2E (ex.: `VITE_E2E=1` zera atrasos), documentado.
2. Execução repetida do E2E não depende de dados de execução anterior (banco limpo + seed próprio).
3. CI falha de verdade quando cobertura < 70%, lint falha, build falha ou E2E falha.
4. `backend/htmlcov/` removido do repositório e ignorado; evidência de cobertura continua acessível (artefato + resumo).
5. Docs não prometem nada que o código não faz (cada rota/coleção/índice citado existe).

---

### Task 1: Backend — CI, cobertura publicada e integração com Mongo (EV-05)

**Files:** Modify `.github/workflows/backend-ci.yml` (jobs `unit` com cobertura → `coverage.xml` + `htmlcov` como artefato + resumo `coverage report` no `$GITHUB_STEP_SUMMARY`; job `integration` com service `mongo:7` rodando `-m mongo` com `MONGO_TEST_URI`), `.gitignore` (`backend/htmlcov/`, `coverage.xml`), remover `backend/htmlcov/` do índice (`git rm -r --cached`), `backend/tests/test_mongo_integration.py` (caso do painel no Mongo real: seed de demonstração → números batem com a versão mongomock), `scripts/verify-delivery.sh` (opção `--integration` usando `MONGO_TEST_URI` se definido).

- [ ] Steps: teste de integração do painel (rodar contra o Mongo local `127.0.0.1:27017` com banco descartável); workflow; remover htmlcov; verify. Commits `ci(EV-05): cobertura publicada e integracao com mongo no CI`, `test(EV-32): painel no mongo real`.

---

### Task 2: Frontend — lint e CI (EV-72)

**Files:** Create `frontend/eslint.config.js` (flat: `@eslint/js` recommended, react recommended + jsx-runtime, react-hooks recommended, browser globals, `no-unused-vars` erro com `argsIgnorePattern: "^_"`), `.github/workflows/frontend-ci.yml` (`npm ci`, `npm run lint`, `npm run build`, gatilhos em `frontend/**`). Modify `frontend/package.json` (scripts `lint`, devDeps), código que o lint acusar (corrigir pela causa; `eslint-disable` só com comentário do motivo), `scripts/verify-delivery.sh` (frontend roda lint antes do build).

- [ ] Steps: config; rodar lint; corrigir; workflow; verify. Commit `ci(EV-72): lint e build do frontend no CI` (+ `fix(EV-72): ...` para correções de lint).

---

### Task 3: E2E com Playwright (EV-70)

**Files:** Create `frontend/playwright.config.js` (`webServer`: backend `uvicorn` com `LLM_PROVIDER=fake`, `MONGO_DB=aep_e2e`, porta 8090; Vite com `VITE_API_URL=http://127.0.0.1:8090` e `VITE_E2E=1`, porta 5190; `reuseExistingServer: !process.env.CI`; Chromium com `--use-fake-ui-for-media-stream --use-fake-device-for-media-stream`), `frontend/e2e/global-setup.js` (limpa `aep_e2e` e roda o seed de demonstração via `python -m scripts.seed_demo --reset` com `MONGO_DB=aep_e2e`), `frontend/e2e/*.spec.js`, `frontend/e2e/fixtures/questionario.txt`. Modify `frontend/src` só para: atrasos de realismo zerados quando `import.meta.env.VITE_E2E === "1"` e seletores acessíveis (sem `data-testid` se papel/rótulo bastarem). Modify `.github/workflows/frontend-ci.yml` (job `e2e` com service `mongo:7`, Python 3.11 + `requirements.txt`, `npx playwright install --with-deps chromium`, upload do relatório em falha), `scripts/verify-delivery.sh --e2e`.

**Cenários:**
1. Pesquisador: lista de roteiros mostra os 4 roteiros do seed → abre "Transporte público na periferia" → lista de entrevistas filtra por concluídas → abre uma → vê transcrição e síntese com citação.
2. Importação: "Subir questionário" com `questionario.txt` → editor preenchido com aviso de revisão → publica → roteiro aparece na lista.
3. Convite + modo texto: abre o convite do roteiro novo (link do modal) → escolhe "Escrever" → responde todas as perguntas até o agradecimento (o fake sempre avança) → pesquisador vê a entrevista concluída na lista e gera a síntese.
4. Painel: abre o painel do roteiro do seed → cartões e gráficos visíveis com números; "Ver dados" mostra tabela; relatório do roteiro já existe no seed ou é gerado.
5. Negativos: convite inexistente mostra "Esse convite não existe ou foi encerrado."; pedido "quero parar" no modo texto encerra com a mensagem de parada.
6. Voz (fumaça): entra pelo convite em "Falar", o microfone falso é aceito e a tela mostra o estado "ouvindo"/botão de gravar sem erro (sem validar áudio).

- [ ] Steps: config + setup + specs; rodar local (`npx playwright test`); workflow; verify `--e2e`. Commits `test(EV-70): e2e dos fluxos principais com playwright`, `ci(EV-70): e2e no CI`.

---

### Task 4: Documentação técnica (EV-06)

**Files:** Create `docs/arquitetura.md` (componentes; sequência de um turno em streaming; grafo LangGraph; providers; decisões e por quê), `docs/banco.md` (4 coleções: campos, exemplo real de documento de cada uma tirado do seed, relacionamentos, índices exatos dos repositórios, pipelines de agregação do painel/listagens, regras de exclusão/cascata, migração v0.1.0), `docs/api.md` (todas as rotas `/api/v1` com método, corpo, resposta, erros; link para `/docs`), `docs/testes.md` (como rodar unit, integração, E2E, cobertura; o que cada suíte cobre; números). Modify `README.md` (seção "Documentação técnica" com links; remove duplicações longas que agora vivem nos docs, mantendo o essencial), `docs/EVOLUCOES.md` (EV-05, EV-06, EV-70, EV-72 → `DONE`; RK-03, RK-04 mitigados).

- [ ] Steps: escrever conferindo o código; verify. Commit `docs(EV-06): documentacao tecnica de arquitetura, banco, api e testes`.
