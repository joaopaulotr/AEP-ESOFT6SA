"""Logs estruturados em JSON, sem conteúdo (EV-62)."""

import json
import logging

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.logging import JsonFormatter, configure_logging
from app.main import app

SEGREDO = "fala-secreta-do-participante"


def _record(**extra) -> logging.LogRecord:
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "mensagem %s", ("a",), None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_formatter_emits_json_with_base_and_allowed_extra_fields():
    line = JsonFormatter().format(
        _record(request_id="abc", status=200, duration_ms=1.5, stage="turno")
    )
    data = json.loads(line)
    assert {"ts", "level", "logger", "msg"} <= data.keys()
    assert data["msg"] == "mensagem a" and data["level"] == "INFO"
    assert (data["request_id"], data["status"], data["duration_ms"], data["stage"]) == (
        "abc",
        200,
        1.5,
        "turno",
    )


def test_formatter_ignores_content_fields():
    line = JsonFormatter().format(_record(texto=SEGREDO, body=SEGREDO, profile={"a": SEGREDO}))
    assert SEGREDO not in line


def test_configure_logging_does_not_replace_existing_handlers():
    root = logging.getLogger()
    before = list(root.handlers)
    configure_logging()
    assert root.handlers == before


def test_middleware_logs_one_line_per_request(caplog, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "fake")
    with TestClient(app) as client:
        sid = client.post("/api/v1/session").json()["session_id"]
        with caplog.at_level(logging.INFO, logger="app.main"):
            r = client.post(f"/api/v1/turn/{sid}?x={SEGREDO}", json={"texto": SEGREDO})
    lines = [x for x in caplog.records if x.name == "app.main" and x.getMessage() == "requisicao"]
    assert len(lines) == 1
    rec = lines[0]
    assert (rec.method, rec.status, rec.session_id) == ("POST", 200, sid)
    assert rec.path.endswith("/turn/{session_id}") and rec.duration_ms >= 0
    assert len(rec.request_id) == 12 and r.headers["X-Request-ID"] == rec.request_id
    assert SEGREDO not in JsonFormatter().format(rec)


def test_middleware_logs_without_session_id_for_other_routes(caplog):
    with TestClient(app) as client, caplog.at_level(logging.INFO, logger="app.main"):
        client.get("/health")
    rec = next(r for r in caplog.records if r.getMessage() == "requisicao")
    assert rec.session_id is None and rec.status == 200
