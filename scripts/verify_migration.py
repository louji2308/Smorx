"""Verify the migrated database equals the ORM model metadata (Phase 2 fusion gate)."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/src"))
sys.path.insert(0, str(ROOT / "packages/behavior/src"))
sys.path.insert(0, str(ROOT / "packages/agent-runtime/src"))

from smorx_behavior.db.base import Base

DB = ROOT / "smorx_generated.db"


def db_tables() -> set[str]:
    conn = sqlite3.connect(DB)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'alembic%'"
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


def model_tables() -> set[str]:
    import smorx_behavior.models  # noqa: F401

    return set(Base.metadata.tables.keys())


def main() -> int:
    mt = model_tables()
    dt = db_tables()
    missing = mt - dt
    extra = dt - mt
    failures: list[str] = []
    if missing:
        failures.append(f"tables absent in DB: {sorted(missing)}")
    if extra:
        failures.append(f"extra tables in DB: {sorted(extra)}")
    from smorx_behavior.db.engine import create_sync_engine
    from sqlalchemy import inspect as sa_inspect

    engine = create_sync_engine(f"sqlite:///{DB}")
    insp = sa_inspect(engine)
    for name in sorted(dt):
        meta_cols = {c.name: str(c.type) for c in Base.metadata.tables[name].columns}
        db_meta = {c["name"]: str(c["type"]) for c in insp.get_columns(name)}
        mismatches = []
        for cn, ct in meta_cols.items():
            if db_meta.get(cn, "").upper() != ct.upper() and ct not in {
                db_meta.get(cn, "").upper()
            }:
                # GUID/Uuid renders as CHAR(32); JSON as JSON - accept known mappings
                if "UUID" in ct.upper() and "CHAR" in db_meta.get(cn, "").upper():
                    continue
                if "JSON" in ct.upper() and "JSON" in db_meta.get(cn, "").upper():
                    continue
                mismatches.append(f"{cn}: model={ct} db={db_meta.get(cn)}")
        if mismatches:
            failures.append(f"{name} column type drift: {mismatches}")

    print(f"model tables : {len(mt)}")
    print(f"db tables    : {len(dt)}")
    print(f"missing      : {sorted(missing) or 'none'}")
    print(f"extra        : {sorted(extra) or 'none'}")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("MIGRATION == METADATA: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
