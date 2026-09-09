import hashlib
import secrets
from uuid import UUID

TOKEN_PREFIX = "siftos"


def issue_service_token(credential_id: UUID) -> str:
    return f"{TOKEN_PREFIX}.{credential_id}.{secrets.token_urlsafe(32)}"


def parse_service_token(token: str) -> UUID:
    try:
        prefix, raw_id, secret = token.split(".", 2)
        credential_id = UUID(raw_id)
    except (ValueError, AttributeError) as exc:
        raise ValueError("invalid service credential") from exc
    if prefix != TOKEN_PREFIX or len(secret) < 32:
        raise ValueError("invalid service credential")
    return credential_id


def hash_service_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
