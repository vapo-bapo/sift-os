from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.partners.models import PartnerStatus
from app.partners.schemas import AgreementCreate, PartnerUpdate
from app.partners.service import calculate_revenue_share, update_partner


@pytest.mark.unit
def test_revenue_share_uses_integer_cents_and_assigns_rounding_remainder_to_sift() -> None:
    split = calculate_revenue_share(
        gross_revenue_cents=101,
        partner_share_bps=2_000,
        sift_share_bps=8_000,
    )

    assert split.partner_share_cents == 20
    assert split.sift_share_cents == 81
    assert split.partner_share_cents + split.sift_share_cents == 101


@pytest.mark.unit
@pytest.mark.parametrize(
    ("partner_bps", "sift_bps"),
    [(2_000, 7_999), (-1, 10_001), (10_001, -1)],
)
def test_revenue_share_rejects_invalid_basis_points(partner_bps: int, sift_bps: int) -> None:
    with pytest.raises(ValueError, match="10,000"):
        calculate_revenue_share(
            gross_revenue_cents=1_000,
            partner_share_bps=partner_bps,
            sift_share_bps=sift_bps,
        )


@pytest.mark.unit
def test_revenue_share_rejects_negative_revenue() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        calculate_revenue_share(
            gross_revenue_cents=-1,
            partner_share_bps=2_000,
            sift_share_bps=8_000,
        )


@pytest.mark.unit
def test_partner_models_use_uuid_identity_and_utc_business_dates() -> None:
    from app.partners.models import Partner, PartnerAgreement, PartnerClient

    partner_id = uuid4()
    agreement_id = uuid4()
    now = datetime.now(UTC)
    partner = Partner(id=partner_id, name="Channel One")
    agreement = PartnerAgreement(
        id=agreement_id,
        partner_id=partner_id,
        version=1,
        effective_from=now,
        partner_share_bps=2_000,
        sift_share_bps=8_000,
        currency="EUR",
    )
    client = PartnerClient(
        partner_id=partner_id,
        agreement_id=agreement_id,
        external_client_id=uuid4(),
        client_name="Customer",
        attributed_at=now,
        gross_revenue_cents=1_000,
        partner_share_cents=200,
        sift_share_cents=800,
        currency="EUR",
    )

    assert partner.id == partner_id
    assert agreement.partner_share_bps + agreement.sift_share_bps == 10_000
    assert client.partner_share_cents + client.sift_share_cents == 1_000


@pytest.mark.unit
def test_partner_lifecycle_contains_every_operational_stage() -> None:
    assert [status.value for status in PartnerStatus] == [
        "prospect",
        "negotiating",
        "signed",
        "onboarding",
        "active",
        "inactive",
        "terminated",
    ]


@pytest.mark.unit
def test_new_agreement_defaults_to_configurable_80_20_split() -> None:
    agreement = AgreementCreate(effective_from=datetime.now(UTC))

    assert agreement.partner_share_bps == 2_000
    assert agreement.sift_share_bps == 8_000


@pytest.mark.unit
def test_signed_and_active_lifecycle_dates_are_distinct() -> None:
    from unittest.mock import Mock

    from app.partners.models import Partner

    partner = Partner(name="Lifecycle Partner", status=PartnerStatus.PROSPECT)
    update_partner(Mock(), partner, PartnerUpdate(status=PartnerStatus.SIGNED))

    assert partner.signed_at is not None
    assert partner.activated_at is None
