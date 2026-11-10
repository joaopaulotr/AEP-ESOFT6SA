import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

/**
 * Configuração única do E2E (usada pelo playwright.config.js, global-setup.js e helpers.js).
 * Caminhos resolvidos a partir deste arquivo, não do diretório de onde o comando foi rodado.
 */
export const BACKEND = fileURLToPath(new URL("../../backend", import.meta.url));

/** Python do backend: E2E_PYTHON, senão o venv (Windows ou Linux/macOS), senão o do PATH. */
function resolverPython() {
    if (process.env.E2E_PYTHON) return process.env.E2E_PYTHON;
    for (const rel of [".venv/Scripts/python.exe", ".venv/bin/python"]) {
        const caminho = fileURLToPath(new URL(`../../backend/${rel}`, import.meta.url));
        if (existsSync(caminho)) return caminho;
    }
    return process.platform === "win32" ? "python" : "python3";
}

export const PYTHON = resolverPython();
export const MONGO_URI = process.env.E2E_MONGO_URI || "mongodb://127.0.0.1:27017";
export const MONGO_DB = "aep_e2e";
export const API_ORIGEM = "http://127.0.0.1:8090";
export const API = `${API_ORIGEM}/api/v1`;
export const WEB = "http://127.0.0.1:5190";

/** Ambiente do backend no E2E: LLM falso e banco próprio (nunca OpenAI, nunca o banco de dev). */
export const ENV_BACKEND = {
    LLM_PROVIDER: "fake",
    MONGO_URI,
    MONGO_DB,
    OPENAI_API_KEY: "test-key",
    FRONTEND_URL: WEB,
    PYTHONIOENCODING: "utf-8",
};
