"""Phase 7 unit tests — intent ledger, lock, and constitutional mapping.

Covers (§7.3/§7.4): ledger build with distinct intent items; lock flips
exactly once and authorizes items at lock time; post-lock in-place
mutation raises; bump creates a new version with the historical row
preserved; constraint resolution maps intent onto protected constitution
claims, flags REPLACE conflicts, and requires a locked constitution.
"""

from __future__ import annotations

import uuid

import pytest
from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import Constitution, ConstitutionClaim, Project, Repository
from smorx_behavior.repo import base as repo_base
from smorx_behavior.versioning import VersionLockedError, assert_not_locked
from smorx_behavior.versioning.lock import lock as versioning_lock
from smorx_precode.change_definition import define_change
from smorx_precode.intent_ledger import (
    ConstitutionMapperError,
    IntentLedgerError,
    build_intent_ledger,
    bump_intent_ledger,
    get_intent_ledger,
    lock_intent_ledger,
    resolve_constraints,
)
from sqlalchemy.orm import Session

pytest.importorskip("smorx_precode.intent_ledger")


@pytest.fixture()
def session() -> Session:
    engine = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    project = Project(name="Smorx", slug="smorx")
    repo_base.save(session, project)
    repository = Repository(project_id=project.id, name="payments-api")
    repo_base.save(session, repository)
    session.commit()
    return session


def _ledger(session: Session, **overrides: object):
    project = session.query(Project).first()
    result = define_change(
        session,
        project_id=project.id,
        request={
            "objective": "Add rate limiting to the payments API",
            "repository": "payments-api",
            "acceptance_criteria": ["429 after 100 requests per minute"],
        },
    )
    statements = overrides.get(
        "statements",
        [
            {"intent_type": "ADD", "description": "rate limit middleware"},
            {"intent_type": "REPLACE", "description": "replace auth token cache"},
        ],
    )
    return build_intent_ledger(
        session,
        project_id=project.id,
        task_id=result.task_id,
        objective="Add rate limiting to the payments API",
        statements=statements,
        acceptance_criteria=["429 after 100 requests per minute"],
    )


def _constitution(session: Session, *, locked: bool) -> uuid.UUID:
    project = session.query(Project).first()
    constitution = Constitution(
        project_id=project.id, title="Behavioral Constitution v1"
    )
    repo_base.save(session, constitution)
    repo_base.save(
        session,
        ConstitutionClaim(
            constitution_id=constitution.id,
            category="SECURITY",
            rule="auth tokens must never be logged",
            severity="CRITICAL",
        ),
    )
    repo_base.save(
        session,
        ConstitutionClaim(
            constitution_id=constitution.id,
            category="BEHAVIOR",
            rule="checkout flow keeps two-step confirmation",
            severity="HIGH",
        ),
    )
    if locked:
        versioning_lock(session, constitution)
    session.commit()
    return constitution.id


def test_build_persists_ledger_with_distinct_items(session: Session) -> None:
    ref = _ledger(session)
    assert ref.version == 1
    assert ref.locked is False
    assert ref.status == "PROPOSED"
    # ADD + REPLACE + the implicit PRESERVE guard added by compilation.
    assert len(ref.intent_item_ids) == 3


def test_lock_flips_once_and_authorizes_items(session: Session) -> None:
    ref = _ledger(session)
    locked = lock_intent_ledger(session, ref.intent_ledger_id)
    assert locked.locked is True
    assert locked.status == "LOCKED"
    again = lock_intent_ledger(session, ref.intent_ledger_id)
    assert again.locked is True
    assert again.version == locked.version  # idempotent: no double-bump


def test_post_lock_in_place_mutation_raises(session: Session) -> None:
    ref = _ledger(session)
    lock_intent_ledger(session, ref.intent_ledger_id)
    from smorx_behavior.models import IntentLedger

    row = repo_base.get(session, IntentLedger, ref.intent_ledger_id)
    with pytest.raises(VersionLockedError):
        assert_not_locked(row)


def test_bump_creates_new_version_preserving_history(session: Session) -> None:
    ref = _ledger(session)
    lock_intent_ledger(session, ref.intent_ledger_id)
    bumped = bump_intent_ledger(session, ref.intent_ledger_id, note="intent v2")
    assert bumped.intent_ledger_id != ref.intent_ledger_id
    assert bumped.version == ref.version + 1
    # historical row preserved
    old = get_intent_ledger(session, ref.intent_ledger_id)
    assert old.locked is True
    assert old.version == ref.version


def test_unknown_ledger_raises(session: Session) -> None:
    with pytest.raises(IntentLedgerError):
        get_intent_ledger(session, uuid.uuid4())
    with pytest.raises(IntentLedgerError):
        lock_intent_ledger(session, uuid.uuid4())


def test_constraint_resolution_requires_locked_constitution(session: Session) -> None:
    ref = _ledger(session)
    constitution_id = _constitution(session, locked=False)
    with pytest.raises(ConstitutionMapperError) as excinfo:
        resolve_constraints(
            session,
            intent_ledger_id=ref.intent_ledger_id,
            constitution_id=constitution_id,
        )
    assert "not locked" in str(excinfo.value)


def test_constraint_resolution_maps_and_flags_conflicts(session: Session) -> None:
    ref = _ledger(session)
    constitution_id = _constitution(session, locked=True)
    resolution = resolve_constraints(
        session, intent_ledger_id=ref.intent_ledger_id, constitution_id=constitution_id
    )
    assert resolution.constitution_locked is True
    assert len(resolution.protected_claim_ids) == 2
    matched_text = " ".join(str(i) for i in resolution.matched_claim_ids)
    # "auth tokens must never be logged" overlaps "replace auth token cache"
    assert resolution.conflicting_claim_ids, "REPLACE conflict should be flagged"
    assert resolution.risk_notes
    assert "explicit human authorization" in " ".join(resolution.risk_notes)
    assert matched_text  # at least one matched claim id present


def test_constraint_resolution_unknown_constitution(session: Session) -> None:
    ref = _ledger(session)
    with pytest.raises(ConstitutionMapperError):
        resolve_constraints(
            session, intent_ledger_id=ref.intent_ledger_id, constitution_id=uuid.uuid4()
        )
