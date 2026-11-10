import { defineConfig, devices } from "@playwright/test";
import { API_ORIGEM, BACKEND, ENV_BACKEND, PYTHON, WEB } from "./e2e/ambiente.js";

// E2E: backend real (LLM_PROVIDER=fake, banco aep_e2e) + Vite com VITE_E2E=1 (sem atrasos de realismo).
// Nunca usa OpenAI nem o banco de desenvolvimento. Veja e2e/README.md.
export default defineConfig({
    testDir: "e2e",
    globalSetup: "./e2e/global-setup.js",
    fullyParallel: false,
    workers: 1, // banco compartilhado
    retries: process.env.CI ? 1 : 0,
    timeout: 60_000,
    expect: { timeout: 15_000 },
    reporter: [["list"], ["html", { open: "never" }]],
    use: {
        baseURL: WEB,
        trace: "retain-on-failure",
        permissions: ["microphone"],
        launchOptions: {
            args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
        },
    },
    projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
    // Nunca reaproveita servidores já abertos: um backend de dev nas mesmas portas usaria outro
    // banco/provider, e um Vite sem VITE_E2E=1 teria os atrasos de realismo ligados.
    webServer: [
        {
            command: `"${PYTHON}" -m uvicorn app.main:app --port 8090`,
            cwd: BACKEND,
            url: `${API_ORIGEM}/health`,
            reuseExistingServer: false,
            timeout: 60_000,
            env: ENV_BACKEND,
        },
        {
            command: "npm run dev -- --host 127.0.0.1 --port 5190 --strictPort",
            url: WEB,
            reuseExistingServer: false,
            timeout: 60_000,
            env: { VITE_API_URL: API_ORIGEM, VITE_E2E: "1" },
        },
    ],
});
