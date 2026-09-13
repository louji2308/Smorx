"""Integration tests: certificate relationship, evidence binding traversal, and
immutability.

Covers the Phase 2 "certificate relationship tests" requirement: the
certificate binds evidence + behavioral delta + change through real FKs, the
traversal returns evidence ids and hashes, the catalog query resolves the
certificate for a change, and the locked certificate is immutable through the
versioning API (ADR-0005: bumping a locked object creates a new identity that
never mutates the historical row).

Self-contained: synchronous in-memory SQLite, no dependency on other test
modules. Uses the real evidence/provenance and versioning services that the
parallel agents published.
"""

from __future__ import annotations

import pytest
from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.evidence.provenance import certificate_traversal
from smorx_behavior.models import BehavioralDelta, Certificate, Change
from smorx_behavior.repo import catalog
from smorx_behavior.repo.base import get
from smorx_behavior.seed.demo import build_seed
from smorx_behavior.versioning.lock import (
    VersionLockedError,
    assert_not_locked,
    is_locked,
)
from smorx_behavior.versioning.service import bump, get_lineage
from sqlalchemy import event
from sqlalchemy.orm import Session


@pytest.fixture()
def engine() -> object:
    eng = create_sync_engine("sqlite:///:memory:")
    event.listen(
        eng,
        "connect",
        lambda raw_conn, _: raw_conn.execute("PRAGMA foreign_keys=ON"),
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine: object) -> Session:
    with Session(engine) as sess:
        yield sess


def test_certificate_binds_evidence_delta_and_change(session: Session) -> None:
    report = build_seed(session)

    certificate = get(session, Certificate, report.certificate_id)
    assert certificate is not None
    assert certificate.task_id == report.task_id
    assert certificate.project_id == report.project_id
    assert certificate.claim_id == report.claim_id

    delta = get(session, BehavioralDelta, report.delta_id)
    assert delta is not None
    assert delta.change_id == report.change_id
    assert delta.certificate_id == report.certificate_id
    assert delta.evidence_id is not None

    change = get(session, Change, report.change_id)
    assert change is not None
    assert certificate.behavioral_deltas[0].change_id == change.id


def test_certificate_traversal_returns_evidence_ids_and_hashes(
    session: Session,
) -> None:
    report = build_seed(session)

    certificate = get(session, Certificate, report.certificate_id)
    assert certificate is not None

    chain = certificate.claim.evidence_items
    assert {ev.id for ev in chain} <= set(report.evidence_ids)
    for ev in chain:
        assert len(ev.hash) == 64
        assert isinstance(ev.hash, str)

    binding = certificate_traversal(certificate)
    assert binding["certificate"]["certificate_key"] == certificate.certificate_key
    assert binding["certificate"]["status"] == "CERTIFIED"
    assert binding["certificate"]["evidence_hash"] == certificate.evidence_hash
    assert binding["claim"]["id"] == str(report.claim_id)

    evidence_rows = binding["evidence"]
    assert len(evidence_rows) >= 4
    assert certificate.evidence_hash in {item["hash"] for item in evidence_rows}
    for item in evidence_rows:
        assert len(item["hash"]) == 64
        assert item["id"] in {str(eid) for eid in report.evidence_ids}

    delta_rows = binding["deltas"]
    assert len(delta_rows) == 1
    assert delta_rows[0]["id"] == str(report.delta_id)
    assert delta_rows[0]["direction"] == "DECREASED"
    assert delta_rows[0]["observed"] is True

    memory_rows = binding["memory_updates"]
    assert len(memory_rows) == 1
    assert memory_rows[0]["id"] == str(report.memory_update_id)


def test_certificate_for_change_query(session: Session) -> None:
    report = build_seed(session)
    certificates = catalog.certificate_for_change(session, report.change_id)
    assert [c.id for c in certificates] == [report.certificate_id]


def test_certificate_immutable_after_binding(session: Session) -> None:
    report = build_seed(session)
    certificate = get(session, Certificate, report.certificate_id)
    assert certificate is not None

    assert certificate.version == 1
    assert is_locked(certificate) is True

    with pytest.raises(VersionLockedError):
        assert_not_locked(certificate)

    locked_snapshot = get(session, Certificate, report.certificate_id)
    assert locked_snapshot.locked is True
    assert locked_snapshot.version == 1

    next_version = bump(session, certificate, note="reissue after re-verification")
    session.commit()

    assert next_version.id != report.certificate_id
    assert next_version.version == 2
    assert is_locked(next_version) is False
    assert next_version.certificate_key.endswith("@2")

    original = get(session, Certificate, report.certificate_id)
    assert original is not None
    assert original.version == 1
    assert original.locked is True
    assert original.certificate_key == certificate.certificate_key

    lineage = get_lineage(session, Certificate, next_version.id)
    assert lineage == [report.certificate_id, next_version.id]


def test_certificate_schema_columns_exist(session: Session) -> None:
    columns = Certificate.__table__.columns
    for name in (
        "certificate_key",
        "claim_id",
        "verification_plan_id",
        "evidence_hash",
        "version",
        "locked",
    ):
        assert name in columns, name
