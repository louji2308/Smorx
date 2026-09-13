"""Unit tests for the version/lock policy service (plan 2.5, ADR-0005).

Exercises the real versioned models (``Certificate`` for the JSON parent-ref
path, ``Task`` for the text-marker path) on a synchronous in-memory SQLite
engine. No external services, no credentials.

Public contract under test (see ``smorx_behavior/versioning/service.py`` for
the full documented rules):

* new objects default ``version=1``, ``locked=False``;
* ``lock`` is idempotent and permanent; locked rows are immutable references
  (``assert_not_locked`` raises ``VersionLockedError``);
* bumping a LOCKED object creates a NEW identity (new ``id``, ``version+1``,
  parent reference recorded) and never touches the historical row;
* bumping an UNLOCKED object mutates in place (``version+1``, same identity);
* ``snapshot`` returns a JSON-serializable current-state copy;
* ``get_lineage`` returns ordered ids old -> new;
* versions stay ``>= 1`` and increase by exactly 1 across a lineage.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

import pytest
from smorx_behavior.db.base import Base
from smorx_behavior.db.engine import create_sync_engine
from smorx_behavior.models import Certificate, Project, Task
from smorx_behavior.versioning import (
    PARENT_RESERVED_KEY,
    TEXT_MARKER_RE,
    VersioningError,
    VersionLockedError,
    assert_not_locked,
    bump,
    force_set,
    get_lineage,
    is_locked,
    lock,
    snapshot,
)
from smorx_behavior.versioning.service import parent_storage
from sqlalchemy.orm import Session

pytest.importorskip("smorx_behavior.models")
pytest.importorskip("smorx_behavior.db.base")


def _sha256_hex(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@pytest.fixture()
def engine() -> object:
    eng = create_sync_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session(engine: object) -> Session:
    with Session(engine) as sess:
        yield sess


def _seed_certificate(session: Session) -> Certificate:
    certificate = Certificate(
        certificate_key="cert-AUTH-017",
        status="ISSUED",
        owner_scope="CERTIFICATION",
        payload={"claim": "AUTH-017 token refresh hardened", "tests_passed": 42},
        issued_at=datetime.now(UTC),
        evidence_hash=_sha256_hex("tests/test_auth.py:42-passed"),
    )
    session.add(certificate)
    session.commit()
    return certificate


def _seed_task(session: Session, title: str = "Fix AUTH-017 token refresh") -> Task:
    project = Project(name="Payments API", slug="payments-api")
    task = Task(project=project, title=title, status="CREATED", priority="NORMAL")
    session.add_all([project, task])
    session.commit()
    return task


def test_new_versioned_objects_default_to_version_1_unlocked(session: Session) -> None:
    certificate = _seed_certificate(session)
    task = _seed_task(session)

    assert certificate.version == 1
    assert is_locked(certificate) is False
    assert task.version == 1
    assert is_locked(task) is False


def test_lock_is_idempotent_and_permanent(session: Session) -> None:
    certificate = _seed_certificate(session)

    lock(session, certificate)
    assert certificate.locked is True
    assert is_locked(certificate) is True

    lock(session, certificate)  # idempotent: no-op, never raises
    assert certificate.locked is True


def test_assert_not_locked_raises_with_clear_message(session: Session) -> None:
    certificate = _seed_certificate(session)
    assert_not_locked(certificate)  # unlocked: no-op

    lock(session, certificate)
    with pytest.raises(VersionLockedError) as excinfo:
        assert_not_locked(certificate)
    message = str(excinfo.value)
    assert "Certificate" in message
    assert str(certificate.id) in message
    assert excinfo.value.name == "Certificate"
    assert excinfo.value.key == certificate.id


def test_bump_locked_certificate_creates_new_identity_json_path(
    session: Session,
) -> None:
    original = _seed_certificate(session)
    lock(session, original)

    new_cert = bump(session, original, note="post-lock correction")

    old_id = original.id
    assert new_cert.id != old_id
    assert new_cert.version == 2
    assert new_cert.locked is False

    # Old row is untouched: same identity, version, and full content.
    assert original.locked is True
    assert original.version == 1
    assert original.status == "ISSUED"
    assert original.payload == {
        "claim": "AUTH-017 token refresh hardened",
        "tests_passed": 42,
    }

    # New row inherits parent data and records the parent reference in payload.
    assert new_cert.status == "ISSUED"
    assert new_cert.payload["claim"] == "AUTH-017 token refresh hardened"
    ref = new_cert.payload[PARENT_RESERVED_KEY]
    assert ref["id"] == str(old_id)
    assert ref["version"] == 1
    assert ref["note"] == "post-lock correction"

    # Unique identity column is re-bound to the new version, never reused.
    assert new_cert.certificate_key == "cert-AUTH-017@2"

    # Both rows persist: one version-1 history row, one version-2 identity.
    assert session.get(Certificate, old_id) is not None
    assert session.get(Certificate, new_cert.id) is not None


def test_bump_locked_task_records_text_marker_parent_path(session: Session) -> None:
    task = _seed_task(session)
    lock(session, task)

    new_task = bump(session, task)

    assert new_task.id != task.id
    assert new_task.version == 2
    assert task.version == 1
    assert task.locked is True
    assert new_task.title == "Fix AUTH-017 token refresh"
    assert new_task.status == "CREATED"

    marker = TEXT_MARKER_RE.search(new_task.description or "")
    assert marker is not None
    assert marker.group(1) == str(task.id)
    assert marker.group(2) == "1"
    assert new_task.description == f"[version_parent:{task.id};from_version:1]"


def test_bump_unlocked_mutates_in_place_and_stays_monotonic(session: Session) -> None:
    certificate = _seed_certificate(session)

    bumped = bump(session, certificate)
    assert bumped is certificate
    assert bumped.id == certificate.id
    assert bumped.version == 2
    assert bumped.locked is False

    lock(session, certificate)
    next_identity = bump(session, certificate)
    assert next_identity.id != certificate.id
    assert next_identity.version == 3
    assert certificate.version == 2  # history preserved under lock

    lineage = get_lineage(session, Certificate, next_identity.id)
    assert [lineage[0], lineage[1]] == [certificate.id, next_identity.id]
    versions = [session.get(Certificate, rid).version for rid in lineage]
    assert versions == [2, 3]
    assert versions == list(range(min(versions), max(versions) + 1))


def test_snapshot_round_trips_json(session: Session) -> None:
    certificate = _seed_certificate(session)
    lock(session, certificate)

    snap = snapshot(certificate)
    reloaded = json.loads(json.dumps(snap))

    assert reloaded == snap
    assert snap["version"] == 1
    assert snap["locked"] is True
    assert snap["id"] == str(certificate.id)
    assert snap["certificate_key"] == "cert-AUTH-017"
    assert snap["status"] == "ISSUED"
    assert snap["payload"] == {
        "claim": "AUTH-017 token refresh hardened",
        "tests_passed": 42,
    }
    assert snap["_type"] == "Certificate"
    assert isinstance(snap["issued_at"], str)


def test_get_lineage_ordered_old_to_new_text_path(session: Session) -> None:
    task = _seed_task(session)
    lock(session, task)
    v2 = bump(session, task)
    lock(session, v2)
    v3 = bump(session, v2)

    lineage = get_lineage(session, Task, v3.id)
    assert lineage == [task.id, v2.id, v3.id]
    assert len(lineage) == 3
    assert lineage[0] != lineage[1] != lineage[2]

    versions = [session.get(Task, rid).version for rid in lineage]
    assert versions == [1, 2, 3]
    assert all(v >= 1 for v in versions)
    assert versions == [versions[0] + i for i in range(len(versions))]


def test_get_lineage_on_single_unversioned_identity(session: Session) -> None:
    certificate = _seed_certificate(session)
    assert get_lineage(session, Certificate, certificate.id) == [certificate.id]


def test_get_lineage_rejects_missing_row(session: Session) -> None:
    missing = uuid.uuid4()
    with pytest.raises(VersioningError, match="does not exist"):
        get_lineage(session, Certificate, missing)


def test_bump_rejects_version_below_1(session: Session) -> None:
    certificate = _seed_certificate(session)
    certificate.version = 0
    with pytest.raises(VersioningError, match=r">= 1"):
        bump(session, certificate)


def test_force_set_is_controlled_repair_path(session: Session) -> None:
    certificate = _seed_certificate(session)
    lock(session, certificate)
    assert certificate.locked is True

    with pytest.warns(UserWarning, match="force_set"):
        force_set(session, certificate, locked=False)
    assert certificate.locked is False

    with pytest.warns(UserWarning, match="force_set"):
        force_set(session, certificate, version=7)
    assert certificate.version == 7

    with pytest.raises(VersioningError, match=">= 1"):
        force_set(session, certificate, version=0)


def test_parent_storage_field_selection_is_documented(session: Session) -> None:
    certificate = _seed_certificate(session)
    assert parent_storage(certificate) == ("json", "payload")

    task = _seed_task(session)
    assert parent_storage(task) == ("text", "description")
