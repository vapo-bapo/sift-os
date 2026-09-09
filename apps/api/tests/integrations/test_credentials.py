from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.products.credentials import hash_service_token, issue_service_token, parse_service_token
from app.products.models import Product
from app.products.schemas import CredentialCreate
from app.products.service import (
    authenticate_service_token,
    create_credential,
    revoke_credential,
    rotate_credential,
)
from app.staff.models import StaffMember
from app.staff.roles import Department


@pytest.mark.unit
def test_service_token_can_be_verified_without_storing_plaintext() -> None:
    credential_id = uuid4()
    plaintext = issue_service_token(credential_id)
    parsed_id = parse_service_token(plaintext)

    assert parsed_id == credential_id
    assert hash_service_token(plaintext) == hash_service_token(plaintext)
    assert plaintext not in hash_service_token(plaintext)


@pytest.mark.unit
@pytest.mark.parametrize("token", ["", "Bearer x", "siftos.not-a-uuid.secret", "wrong.value.value"])
def test_malformed_service_token_is_rejected(token: str) -> None:
    with pytest.raises(ValueError, match="credential"):
        parse_service_token(token)


@pytest.mark.unit
def test_tokens_issued_for_same_credential_are_unique() -> None:
    credential_id = uuid4()

    assert issue_service_token(credential_id) != issue_service_token(credential_id)


@pytest.mark.unit
def test_credential_expiry_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        CredentialCreate(name="ARGUS production", expires_at=datetime.now())


@pytest.mark.integration
def test_revoked_credential_cannot_authenticate_or_be_rotated_again(
    db_session: Session,
) -> None:
    staff = StaffMember(
        platform_user_id=uuid4(),
        display_name="Product Admin",
        department=Department.CODING,
        active=True,
    )
    db_session.add(staff)
    db_session.flush()
    product = db_session.scalar(select(Product).where(Product.code == "ARGUS"))
    assert product is not None
    credential, token = create_credential(
        db_session,
        product=product,
        name="ARGUS production",
        actor_id=staff.id,
    )
    assert authenticate_service_token(db_session, token).id == credential.id
    revoke_credential(
        db_session,
        product_id=product.id,
        credential_id=credential.id,
        actor_id=staff.id,
    )

    with pytest.raises(ApiError) as auth_error:
        authenticate_service_token(db_session, token)
    assert auth_error.value.status_code == 401
    with pytest.raises(ApiError) as rotate_error:
        rotate_credential(
            db_session,
            product=product,
            credential_id=credential.id,
            actor_id=staff.id,
        )
    assert rotate_error.value.status_code == 409
