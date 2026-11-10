import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

// E2E: backend real (LLM_PROVIDER=fake, banco aep_e2e) + Vite com VITE_E2E=1 (sem atrasos de realismo).
// Nunca usa OpenAI nem o banco de desenvolvimento. Veja e2e/README.md.
const PYTHON = process.env.E2E_PYTHON || (process.platform === "win32" ? path.resolve("../backend/.venv/Scripts/python") : "python");
const MONGO_URI = process.env.E2E_MONGO_URI || "mongodb://127.0.0.1:27017";
const API = "http://127.0.0.1:8090";
const WEB = "http://127.0.0.1:5190";

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
    webServer: [
        {
            command: `"${PYTHON}" -m uvicorn app.main:app --port 8090`,
            cwd: "../backend",
            url: `${API}/health`,
            reuseExistingServer: !process.env.CI,
            timeout: 60_000,
            env: {
                LLM_PROVIDER: "fake",
                MONGO_URI,
                MONGO_DB: "aep_e2e",
                OPENAI_API_KEY: "test-key",
                FRONTEND_URL: WEB,
            },
        },
        {
            command: "npm run dev -- --host 127.0.0.1 --port 5190 --strictPort",
            url: WEB,
            reuseExistingServer: !process.env.CI,
            timeout: 60_000,
            env: { VITE_API_URL: API, VITE_E2E: "1" },
        },
    ],
});
