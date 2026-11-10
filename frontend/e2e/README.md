# Testes E2E (Playwright)

Rodar: `bash scripts/verify-delivery.sh --e2e` (instala o Chromium, usa o Python do venv) ou
`cd frontend && npx playwright install chromium && npx playwright test`.
Requer um MongoDB em `127.0.0.1:27017` (ou `E2E_MONGO_URI`) e o venv do backend em
`backend/.venv` (Windows ou Linux/macOS; ou `E2E_PYTHON` apontando para outro Python).

- Configuração num lugar só: `e2e/ambiente.js` (portas, URL da API, Python, env do backend). O
  `playwright.config.js`, o `global-setup.js` e os `helpers.js` importam dele.
- Backend sobe com `LLM_PROVIDER=fake` e banco **`aep_e2e`** (nunca o de desenvolvimento, nunca OpenAI).
- `reuseExistingServer: false` nos dois servidores: as portas 8090 (API) e 5190 (Vite) precisam estar
  livres. Um servidor de dev nelas usaria outro banco ou ficaria sem `VITE_E2E=1`, então o teste falha
  de propósito em vez de rodar contra ele.
- `global-setup.js` esvazia as coleções do `aep_e2e` e roda `python -m scripts.seed_demo --reset`:
  cada execução começa do mesmo estado.
- Vite sobe com `VITE_E2E=1` (`src/utils/e2e.js`, só vale no servidor de dev): zera o atraso de
  "pensar", a digitação letra a letra, os fillers de voz e o incentivo por silêncio. Os testes esperam
  pelo estado da tela; a única espera fixa (05) confirma que a tela **não** sai sozinha no acolhimento.
- `workers: 1`, ordem por nome de arquivo; cada cenário que escreve cria o próprio roteiro pela API
  (título único), então um retry não colide com a tentativa anterior.
- Microfone: flags `--use-fake-ui-for-media-stream --use-fake-device-for-media-stream` (tom contínuo) +
  STT/TTS falsos do backend. `06-voz` faz um ciclo completo (gravar → confirmar → próxima fala) e o caso
  de microfone negado; os cenários novos falham em erro de console (`vigiarConsole`).
