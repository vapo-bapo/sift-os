import secrets

CSRF_HEADER_NAME = "X-CSRF-Token"


def csrf_values_match(cookie_value: str | None, header_value: str | None) -> bool:
    if cookie_value is None or header_value is None:
        return False
    return secrets.compare_digest(cookie_value, header_value)
