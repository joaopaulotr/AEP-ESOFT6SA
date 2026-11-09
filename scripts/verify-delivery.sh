#!/usr/bin/env bash
# Verificação determinística de entrega do AEP ESOFT6S.
# Uso: bash scripts/verify-delivery.sh [--backend | --frontend]
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

verify_frontend() {
  step "Frontend: instalar dependências e build (vite)"
  (cd "$ROOT/frontend" && npm ci --no-audit --no-fund --silent && npm run build --silent) \
    || fail "build do frontend"
}

verify_hygiene() {
  step "Higiene: arquivos que nunca devem ser commitados"
  if git -C "$ROOT" ls-files | grep -E '(^|/)\.env$|\.coverage$|(^|/)\.reviews/|(^|/)\.superpowers/' ; then
    fail "arquivo proibido versionado (veja a lista acima)"
  fi
}

case "$MODE" in
  --backend)  verify_backend ;;
  --frontend) verify_frontend ;;
  all)        verify_hygiene; verify_backend; verify_frontend ;;
  *)          fail "opção desconhecida: $MODE (use --backend, --frontend ou nada)" ;;
esac

printf '\n[OK] verificação concluída (%s)\n' "$MODE"
