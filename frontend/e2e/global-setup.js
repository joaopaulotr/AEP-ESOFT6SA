import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PYTHON = process.env.E2E_PYTHON || (process.platform === "win32" ? path.resolve("../backend/.venv/Scripts/python") : "python");
const BACKEND = fileURLToPath(new URL("../../backend", import.meta.url));
const ENV = {
    ...process.env,
    LLM_PROVIDER: "fake",
    MONGO_URI: process.env.E2E_MONGO_URI || "mongodb://127.0.0.1:27017",
    MONGO_DB: "aep_e2e",
    OPENAI_API_KEY: "test-key",
    PYTHONIOENCODING: "utf-8",
};

// Esvazia as coleções do banco aep_e2e (mantém os índices) para a execução não depender da anterior.
const LIMPAR = `
import os
from pymongo import MongoClient
db = MongoClient(os.environ["MONGO_URI"])[os.environ["MONGO_DB"]]
assert db.name == "aep_e2e"
for nome in db.list_collection_names():
    db[nome].delete_many({})
`;

export default function globalSetup() {
    const py = PYTHON;
    const opts = { cwd: BACKEND, env: ENV, stdio: "inherit" };
    execFileSync(py, ["-c", LIMPAR], opts);
    execFileSync(py, ["-m", "scripts.seed_demo", "--reset"], opts);
}
