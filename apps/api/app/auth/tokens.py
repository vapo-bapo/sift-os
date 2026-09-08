import hashlib
import hmac
import secrets

from pydantic import SecretStr


def new_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(raw_token: str, secret: SecretStr) -> str:
    return hmac.new(
        secret.get_secret_value().encode(),
        raw_token.encode(),
        hashlib.sha256,
    ).hexdigest()
