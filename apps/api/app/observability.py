from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

_LOGGER = logging.getLogger("smorx.infra")

_FIELD = r"([\w]*[_-]?(?:api[_-]?key|password|secret|token|authorization|bearer))"
_SEP = r"(['\"]?\s*[:=]\s*)"
_QUOTE = r"(['\"]?)"
_VALUE = r"((?:bearer\s+)?[^\s'\",]+)"
_FIELD_VALUE_PATTERN = re.compile(f"(?i){_FIELD}{_SEP}{_QUOTE}{_VALUE}")
_BEARER_PATTERN = re.compile(r"(?i)((?<![\w])bearer)\s+(\"[^\"\n]*\"|'[^'\n]*'|[^\s'\",]+)")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def redact_secrets(text: str) -> str:
    """Mask credential-like values so traces never leak secrets."""

    def _mask_field(m: re.Match[str]) -> str:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}<redacted>"

    def _mask_bearer(m: re.Match[str]) -> str:
        return f"{m.group(1)} <redacted>"

    out = _FIELD_VALUE_PATTERN.sub(_mask_field, text)
    return _BEARER_PATTERN.sub(_mask_bearer, out)


@dataclass
class TraceContext:
    request_id: str = field(default_factory=lambda: new_id("req"))
    run_id: str = field(default_factory=lambda: new_id("run"))
    operation_id: str = field(default_factory=lambda: new_id("op"))

    def to_dict(self) -> dict[str, str]:
        return {
            "request_id": self.request_id,
            "run_id": self.run_id,
            "operation_id": self.operation_id,
        }


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


@contextmanager
def trace_operation(
    name: str,
    ctx: TraceContext,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> Iterator[None]:
    """Record a start/end trace for one infrastructure operation."""
    started = now_iso()
    _LOGGER.info(
        "operation_start",
        extra={
            "event": "operation_start",
            "operation": name,
            "started_at": started,
            **ctx.to_dict(),
            "provider": provider,
            "model": model,
        },
    )
    try:
        yield
    except Exception as exc:  # noqa: BLE001 - tracing must never hide failures
        _LOGGER.warning(
            "operation_failed",
            extra={
                "event": "operation_failed",
                "operation": name,
                "started_at": started,
                "ended_at": now_iso(),
                "error": type(exc).__name__,
                "error_message": redact_secrets(str(exc)),
                **ctx.to_dict(),
            },
        )
        raise
    else:
        _LOGGER.info(
            "operation_end",
            extra={
                "event": "operation_end",
                "operation": name,
                "started_at": started,
                "ended_at": now_iso(),
                **ctx.to_dict(),
            },
        )


def log_event(event: str, ctx: TraceContext, **fields: Any) -> None:
    _LOGGER.info(
        event,
        extra={
            "event": event,
            **ctx.to_dict(),
            **{k: redact_secrets(str(v)) if isinstance(v, str) else v for k, v in fields.items()},
        },
    )


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        "%(event)s %(request_id)s %(run_id)s %(operation_id)s"
    )
    handler.setFormatter(formatter)
    # Third-party loggers (uvicorn, openai, contree) do not populate our
    # trace fields; inject empty defaults so formatting never KeyErrors.
    handler.addFilter(_TraceFieldFilter())
    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers = [handler]
    _LOGGER.setLevel(level.upper())


class _TraceFieldFilter(logging.Filter):
    """Provide default values for trace fields absent on foreign log records."""

    _DEFAULTS = {
        "event": "",
        "request_id": "",
        "run_id": "",
        "operation_id": "",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        for key, default in self._DEFAULTS.items():
            if not hasattr(record, key):
                setattr(record, key, default)
        return True
