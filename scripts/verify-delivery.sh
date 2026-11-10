#!/usr/bin/env bash
# Verificação determinística de entrega do AEP ESOFT6S.
# Uso: bash scripts/verify-delivery.sh [--backend | --frontend | --integration | --e2e]
#   --integration  pytest -m mongo (exige MONGO_TEST_URI)
#   --e2e          Playwright no frontend (exige frontend/playwright.config.js)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-all}"

step() { printf '\n==> %s\n' "$1"; }
fail() { printf '\n[FALHOU] %s\n' "$1" >&2; exit 1; }

python_bin() {
  for candidate in \
    "$ROOT/backend/.venv/Scripts/python.exe" \
    "$ROOT/backend/.venv/bin/python"; do
    [ -x "$candidate" ] && { echo "$candidate"; return; }
  done
  command -v python3 || command -v python || fail "Python não encontrado"
}

verify_backend() {
  local py
  py="$(python_bin)"
  step "Backend: pytest + cobertura (>= 70%) com $("$py" --version 2>&1)"
  (cd "$ROOT/backend" && OPENAI_API_KEY="${OPENAI_API_KEY:-test-key}" \
    "$py" -m pytest -q --cov-fail-under=70) || fail "testes ou cobertura do backend"

  step "Backend: nenhum arquivo fora da medição de cobertura"
  if grep -qE '^\s*omit\s*=' "$ROOT/backend/pyproject.toml"; then
    fail "pyproject.toml tem 'omit' na cobertura — teste o código em vez de excluí-lo"
  fi
}

verify_integration() {
  local py
  py="$(python_bin)"
  [ -n "${MONGO_TEST_URI:-}" ] \
    || fail "defina MONGO_TEST_URI (ex.: mongodb://127.0.0.1:27017/x) para rodar --integration"
  step "Backend: integração com MongoDB real (pytest -m mongo)"
  (cd "$ROOT/backend" && OPENAI_API_KEY="${OPENAI_API_KEY:-test-key}" \
    "$py" -m pytest -q -m mongo --no-cov) || fail "testes de integração com MongoDB"
}

verify_frontend() {
  step "Frontend: instalar dependências, lint (0 avisos), testes unitários (vitest) e build (vite)"
  (cd "$ROOT/frontend" && npm ci --no-audit --no-fund --silent \
    && npm run lint --silent && npm test --silent && npm run build --silent) \
    || fail "lint, testes unitários ou build do frontend"
}

verify_e2e() {
  [ -f "$ROOT/frontend/playwright.config.js" ] \
    || fail "frontend/playwright.config.js não existe — E2E ainda não configurado"
  local py
  py="$(python_bin)"
  step "Frontend: testes E2E (Playwright) com o backend em $("$py" --version 2>&1)"
  (cd "$ROOT/frontend" && npm ci --no-audit --no-fund --silent \
    && npx playwright install chromium \
    && E2E_PYTHON="$py" npx playwright test) \
    || fail "testes E2E"
}

verify_hygiene() {
  step "Higiene: arquivos que nunca devem ser commitados"
  if git -C "$ROOT" ls-files | grep -E '(^|/)\.env$|\.coverage$|(^|/)coverage\.xml$|(^|/)htmlcov/|(^|/)playwright-report/|(^|/)test-results/|(^|/)\.reviews/|(^|/)\.superpowers/' ; then
    fail "arquivo proibido versionado (veja a lista acima)"
  fi
}

case "$MODE" in
  --backend)     verify_backend ;;
  --frontend)    verify_frontend ;;
  --integration) verify_integration ;;
  --e2e)         verify_e2e ;;
  all)           verify_hygiene; verify_backend; verify_frontend ;;
  *)             fail "opção desconhecida: $MODE (use --backend, --frontend, --integration, --e2e ou nada)" ;;
esac

printf '\n[OK] verificação concluída (%s)\n' "$MODE"
