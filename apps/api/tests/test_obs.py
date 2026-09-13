from __future__ import annotations

import logging

from app.observability import TraceContext, configure_logging, new_id, redact_secrets


def test_configured_handler_formats_foreign_records() -> None:
    """Third-party records without trace fields must not KeyError the formatter."""
    configure_logging()
    handler = logging.getLogger().handlers[0]
    record = logging.LogRecord(
        name="uvicorn.error",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="third party says something",
        args=(),
        exc_info=None,
    )
    handler.handle(record)  # runs the filter, then formats + emits
    assert record.__dict__["event"] == ""
    assert record.__dict__["request_id"] == ""


def test_new_id_prefixes() -> None:
    request_id = new_id("req")
    run_id = new_id("run")
    operation_id = new_id("op")
    assert request_id.startswith("req_")
    assert run_id.startswith("run_")
    assert operation_id.startswith("op_")
    assert len(request_id) == len("req_") + 12


def test_new_id_is_unique() -> None:
    assert new_id("req") != new_id("req")


def test_trace_context_to_dict_with_explicit_ids() -> None:
    ctx = TraceContext(request_id="r1", run_id="r2", operation_id="o3")
    assert ctx.to_dict() == {"request_id": "r1", "run_id": "r2", "operation_id": "o3"}


def test_trace_context_to_dict_with_defaults() -> None:
    data = TraceContext().to_dict()
    assert set(data) == {"request_id", "run_id", "operation_id"}
    assert data["request_id"].startswith("req_")
    assert data["run_id"].startswith("run_")
    assert data["operation_id"].startswith("op_")


def test_redact_secrets_masks_api_key_colon() -> None:
    assert redact_secrets("api_key: SECRET") == "api_key: <redacted>"


def test_redact_secrets_masks_token_equals() -> None:
    assert redact_secrets("token=SECRET") == "token=<redacted>"


def test_redact_secrets_masks_secret_with_quotes() -> None:
    assert redact_secrets('password="hunter2"') == 'password="<redacted>"'


def test_redact_secrets_masks_inside_larger_payload() -> None:
    redacted = redact_secrets('endpoint=/v1 headers={"api_key": "abc123"} more')
    assert "abc123" not in redacted


def test_redact_secrets_authorization_bearer() -> None:
    redacted = redact_secrets("Authorization: Bearer xyz123")
    assert "<redacted>" in redacted
    assert "Bearer" not in redacted


def test_redact_secrets_leaves_plain_text_untouched() -> None:
    text = "everything is fine here"
    assert redact_secrets(text) == text
