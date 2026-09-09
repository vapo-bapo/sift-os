from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.crm.csv_import import parse_account_csv
from app.crm.schemas import AccountCreate
from app.crm.service import (
    create_account,
    import_accounts,
    preview_account_import,
)
from tests.crm.test_service import _current


@pytest.mark.unit
def test_csv_preview_normalizes_rows_and_detects_duplicates() -> None:
    result = parse_account_csv(
        "name,domain,account_type,lead_score\nAcme,https://www.ACME.test,direct_prospect,40\n"
        "Acme copy,acme.test,direct_prospect,20\n"
    )

    assert len(result.rows) == 2
    assert result.rows[0].normalized_domain == "acme.test"
    assert result.rows[0].valid is True
    assert result.rows[1].valid is False
    assert "duplicate domain in file" in result.rows[1].errors


@pytest.mark.unit
def test_csv_preview_reports_invalid_fields_without_raising() -> None:
    result = parse_account_csv("name,account_type,lead_score\n,invalid,101\n")

    assert result.valid_rows == 0
    assert result.invalid_rows == 1
    assert result.rows[0].errors


@pytest.mark.unit
def test_csv_rejects_more_than_maximum_rows() -> None:
    body = "name\n" + "\n".join(f"Company {index}" for index in range(3))

    result = parse_account_csv(body, max_rows=2)

    assert result.file_errors == ["CSV exceeds the maximum of 2 data rows"]


@pytest.mark.unit
def test_csv_owner_id_is_validated() -> None:
    result = parse_account_csv(f"name,owner_id\nAcme,{uuid4()}\n")
    assert result.rows[0].valid is True


@pytest.mark.integration
def test_csv_preview_detects_domain_already_in_database(db_session: Session) -> None:
    actor = _current(db_session)
    create_account(db_session, actor, AccountCreate(name="Acme", domain="acme.test"))
    db_session.flush()

    preview = preview_account_import(
        db_session, actor, "name,domain\nDuplicate,https://www.acme.test/path\n"
    )

    assert preview.invalid_rows == 1
    assert preview.rows[0].duplicate_account_id is not None
    assert preview.rows[0].errors == ["domain already exists"]


@pytest.mark.integration
def test_confirmed_valid_csv_is_imported(db_session: Session) -> None:
    actor = _current(db_session)

    result = import_accounts(
        db_session,
        actor,
        "name,domain,lead_score\nAcme,acme.test,75\nBeta,beta.test,20\n",
        confirmed=True,
    )

    assert result.imported == 2
    assert len(result.account_ids) == 2


@pytest.mark.integration
def test_import_requires_explicit_confirmation(db_session: Session) -> None:
    actor = _current(db_session)

    with pytest.raises(ApiError) as caught:
        import_accounts(db_session, actor, "name\nAcme\n", confirmed=False)

    assert caught.value.code == "CRM_IMPORT_CONFIRMATION_REQUIRED"
