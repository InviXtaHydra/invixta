"""The JSON log formatter: secrets are redacted, ordinary numbers are not."""

import json
import logging

from app.core.logging import JsonFormatter


def log_line(**extra: object) -> dict[str, object]:
    record = logging.LogRecord("supportai.test", logging.INFO, __file__, 1, "something happened", (), None)
    for key, value in extra.items():
        setattr(record, key, value)
    return json.loads(JsonFormatter().format(record))  # type: ignore[no-any-return]


def test_secrets_are_redacted_but_token_counts_are_kept() -> None:
    line = log_line(password="hunter2", password_hash="$2b$...", api_key="sk-1", access_token="eyJ", authorization="Bearer x",
                    input_tokens=812, output_tokens=64, order_id="10021")  # fmt: skip
    for key in ("password", "password_hash", "api_key", "access_token", "authorization"):
        assert line[key] == "[redacted]", key
    assert line["input_tokens"] == 812 and line["output_tokens"] == 64 and line["order_id"] == "10021"
    assert line["message"] == "something happened" and line["level"] == "INFO"
