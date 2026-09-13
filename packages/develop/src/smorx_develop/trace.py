"""Phase 8.12 — Attributable execution trace.

Builds one hash-chained trace per loop run that binds the full
attribution chain (master prompt §8.12, I3):

    Task → Decision → Tool Invocation → Execution Result → Mutation

Integrity: every entry carries ``sequence`` and ``entry_hash`` where
``entry_hash = sha256(sequence + previous_hash + payload)``. Tampering
with any payload breaks every subsequent hash, and
:func:`verify_trace_integrity` detects it.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Any

from smorx_develop.agent import LoopResult
from smorx_develop.candidates import CandidatePatchRecord
from smorx_develop.execution import ExecutionStats

__all__ = ["ExecutionTrace", "TraceEntry", "build_trace", "verify_trace_integrity"]


@dataclass(frozen=True)
class TraceEntry:
    """One attributable trace entry."""

    sequence: int
    kind: str  # TASK | DECISION | TOOL_INVOCATION | EXECUTION_RESULT | MUTATION
    at: str
    payload: dict[str, Any]
    previous_hash: str
    entry_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "kind": self.kind,
            "at": self.at,
            "payload": self.payload,
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash,
        }


@dataclass(frozen=True)
class ExecutionTrace:
    """The complete hash-chained trace of one loop run."""

    trace_id: str
    task_id: str
    loop_id: str
    entries: tuple[TraceEntry, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "task_id": self.task_id,
            "loop_id": self.loop_id,
            "entries": [entry.as_dict() for entry in self.entries],
        }


def _hash_payload(sequence: int, previous: str, payload: dict[str, Any]) -> str:
    import json

    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(f"{sequence}|{previous}|{canonical}".encode()).hexdigest()


def _entry(sequence: int, previous: str, kind: str, at: str, payload: dict[str, Any]) -> TraceEntry:
    return TraceEntry(
        sequence=sequence,
        kind=kind,
        at=at,
        payload=payload,
        previous_hash=previous,
        entry_hash=_hash_payload(sequence, previous, payload),
    )


def build_trace(
    *,
    task_id: uuid.UUID,
    handoff_id: uuid.UUID,
    result: LoopResult,
    candidate: CandidatePatchRecord | None = None,
) -> ExecutionTrace:
    """Assemble the hash-chained trace from a finished loop run."""
    entries: list[TraceEntry] = []
    previous = "GENESIS"
    sequence = 0

    def _append(kind: str, at: str, payload: dict[str, Any]) -> None:
        nonlocal sequence, previous
        sequence += 1
        entry = _entry(sequence, previous, kind, at, payload)
        entries.append(entry)
        previous = entry.entry_hash

    _append(
        "TASK",
        "",
        {
            "task_id": str(task_id),
            "handoff_id": str(handoff_id),
            "loop_id": result.loop_id,
            "sandbox_id": candidate.sandbox_id if candidate else "",
        },
    )
    for decision in result.decisions:
        _append("DECISION", "", decision.as_dict())
    for mutation in result.mutations:
        _append("MUTATION", "", dict(mutation))
    for record in result.executions:
        _append(
            "EXECUTION_RESULT",
            "",
            {
                "execution_id": record.execution_id,
                "kind": record.kind,
                "command": list(record.command),
                "exit_code": record.exit_code,
                "failure_code": record.failure_code,
                "duration_seconds": record.duration_seconds,
                "timed_out": record.timed_out,
                "passed": record.passed,
            },
        )
    stats = ExecutionStats(result.executions).as_dict()
    _append(
        "TOOL_INVOCATION",
        "",
        {
            "tool": "develop.loop",
            "loop_id": result.loop_id,
            "final_state": result.final_state,
            "termination": result.termination.as_dict(),
            "execution_stats": stats,
        },
    )
    if candidate is not None:
        _append(
            "TOOL_INVOCATION",
            "",
            {
                "tool": "develop.candidate",
                "candidate_id": candidate.candidate_id,
                "candidate_index": candidate.candidate_index,
                "final_state": candidate.final_state,
                "note": "candidate is NOT certified (I7)",
            },
        )
    return ExecutionTrace(
        trace_id=f"trace-{uuid.uuid4().hex[:12]}",
        task_id=str(task_id),
        loop_id=result.loop_id,
        entries=tuple(entries),
    )


def verify_trace_integrity(trace: ExecutionTrace) -> tuple[bool, str]:
    """Recompute the hash chain; return (ok, detail)."""
    previous = "GENESIS"
    for entry in trace.entries:
        expected = _hash_payload(entry.sequence, previous, entry.payload)
        if entry.entry_hash != expected:
            return (
                False,
                f"entry {entry.sequence} payload/hash mismatch: chain broken at "
                f"{entry.entry_hash} (expected {expected})",
            )
        if entry.previous_hash != previous:
            return (
                False,
                f"entry {entry.sequence} previous_hash mismatch: chain reordered",
            )
        previous = entry.entry_hash
    return True, f"chain intact across {len(trace.entries)} entries"
