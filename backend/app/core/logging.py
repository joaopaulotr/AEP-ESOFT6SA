"""Logs estruturados em JSON (EV-62). Só ids, etapas, durações e tipos de erro: nunca conteúdo."""

import json
import logging
import sys
from datetime import datetime, timezone

# Únicos campos extras aceitos: tudo o mais passado em `extra=` é ignorado.
EXTRA_FIELDS = (
    "request_id",
    "method",
    "path",
    "status",
    "duration_ms",
    "session_id",
    "stage",
    "error_type",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for field in EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                data[field] = value
        return json.dumps(data, ensure_ascii=False, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Instala o handler JSON na raiz, só se ninguém configurou antes (não quebra o pytest)."""
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)
