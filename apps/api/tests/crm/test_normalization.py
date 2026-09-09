import pytest

from app.crm.normalization import normalize_domain, normalize_email, normalize_name, normalize_phone


@pytest.mark.unit
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" HTTPS://WWW.Example.COM/path ", "example.com"),
        ("example.com.", "example.com"),
        (None, None),
    ],
)
def test_normalize_domain(value: str | None, expected: str | None) -> None:
    assert normalize_domain(value) == expected


@pytest.mark.unit
def test_normalize_email_and_phone() -> None:
    assert normalize_email(" Sales@Example.COM ") == "sales@example.com"
    assert normalize_phone(" +39 (333) 12-34 ") == "+393331234"


@pytest.mark.unit
def test_normalize_name_removes_accents_and_spacing() -> None:
    assert normalize_name("  Giòrgio   D'Angelo ") == "giorgio d angelo"
