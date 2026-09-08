from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.audit.models import AuditResult
from app.audit.service import record_audit_log
from app.auth.models import UserSession
from app.staff.models import StaffMember, StaffMemberRole
from app.staff.roles import Department, StaffRole

PLATFORM_ID = UUID("4ac5662a-1eaa-4f47-9dae-406eefdf6e40")


def staff(platform_user_id: UUID = PLATFORM_ID) -> StaffMember:
    return StaffMember(
        platform_user_id=platform_user_id,
        display_name="Alessandro Bellucco",
        department=Department.CODING,
    )


@pytest.mark.integration
def test_platform_user_id_is_unique(db_session) -> None:
    db_session.add_all([staff(), staff()])

    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_staff_role_pair_is_unique(db_session) -> None:
    member = staff()
    db_session.add(member)
    db_session.flush()
    db_session.add_all(
        [
            StaffMemberRole(staff_member_id=member.id, role=StaffRole.ADMIN),
            StaffMemberRole(staff_member_id=member.id, role=StaffRole.ADMIN),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_session_identifiers_are_unique(db_session) -> None:
    member = staff()
    db_session.add(member)
    db_session.flush()
    expires_at = datetime.now(UTC) + timedelta(hours=12)
    db_session.add_all(
        [
            UserSession(
                staff_member_id=member.id,
                token_digest="a" * 64,
                csrf_nonce_digest="b" * 64,
                platform_assertion_jti="platform-jti",
                expires_at=expires_at,
            ),
            UserSession(
                staff_member_id=member.id,
                token_digest="a" * 64,
                csrf_nonce_digest="c" * 64,
                platform_assertion_jti="another-jti",
                expires_at=expires_at,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.integration
def test_record_audit_log_persists_append_only_event(db_session) -> None:
    member = staff()
    db_session.add(member)
    db_session.flush()

    audit_log = record_audit_log(
        db_session,
        actor_staff_id=member.id,
        action="staff.roles.updated",
        entity_type="staff_member",
        entity_id=member.id,
        previous={"roles": ["coding"]},
        new={"roles": ["admin", "coding"]},
        request_id="request-123",
        ip_address="127.0.0.1",
        user_agent_summary="pytest",
        result=AuditResult.SUCCESS,
    )
    db_session.flush()

    assert audit_log.id is not None
    assert audit_log.occurred_at.tzinfo is not None
    assert audit_log.previous == {"roles": ["coding"]}
    assert audit_log.new == {"roles": ["admin", "coding"]}


def test_role_and_department_values_are_stable() -> None:
    assert {role.value for role in StaffRole} == {
        "ceo",
        "admin",
        "sales_lead",
        "sales",
        "coding",
    }
    assert {department.value for department in Department} == {"sales", "coding"}


@pytest.mark.integration
def test_staff_defaults_to_active(db_session) -> None:
    member = staff(platform_user_id=uuid4())
    db_session.add(member)
    db_session.flush()

    assert member.active is True
