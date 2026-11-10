# Testes E2E (Playwright)

Rodar: `cd frontend && npx playwright test` (primeira vez: `npx playwright install chromium`).
Pare servidores de dev nas portas 8090/5190 antes de rodar localmente: `reuseExistingServer` os reutilizaria, possivelmente com outro banco.
Requer um MongoDB em `127.0.0.1:27017` (ou `E2E_MONGO_URI`) e o venv do backend (ou `E2E_PYTHON`).

- Backend sobe com `LLM_PROVIDER=fake` e banco **`aep_e2e`** (nunca o de desenvolvimento, nunca OpenAI).
- `global-setup.js` esvazia as coleções do `aep_e2e` e roda `python -m scripts.seed_demo --reset`: cada execução começa do mesmo estado.
- Vite sobe com `VITE_E2E=1` (`src/utils/e2e.js`): zera o atraso de "pensar", a digitação letra a letra, os fillers de voz e o incentivo por silêncio. Os testes esperam pelo estado da tela, nunca por tempo fixo.
- `workers: 1`, ordem por nome de arquivo (03 usa o roteiro publicado em 02; se ele não existir, cria pela API).
- Microfone: flags `--use-fake-ui-for-media-stream --use-fake-device-for-media-stream`.
