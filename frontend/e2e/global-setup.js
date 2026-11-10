import { execFileSync } from "node:child_process";
import { BACKEND, ENV_BACKEND, PYTHON } from "./ambiente.js";

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
    const opts = { cwd: BACKEND, env: { ...process.env, ...ENV_BACKEND }, stdio: "inherit" };
    execFileSync(PYTHON, ["-c", LIMPAR], opts);
    execFileSync(PYTHON, ["-m", "scripts.seed_demo", "--reset"], opts);
}
