from __future__ import annotations

import httpx
import jwt
from jwt import PyJWKClient
from pydantic import ValidationError

from app.auth.schemas import PlatformClaims, PlatformExchange
from app.core.config import Settings
from app.core.errors import ApiError


class AuthFailure(ApiError):
    def __init__(self, code: str, *, status_code: int = 401) -> None:
        messages = {
            "SSO_TICKET_INVALID": "Il ticket SSO non è valido o è scaduto.",
            "SSO_ASSERTION_INVALID": "L'assertion SSO non è valida o è scaduta.",
            "ASSERTION_REPLAYED": "L'assertion SSO è già stata utilizzata.",
            "STAFF_ACCESS_DENIED": "L'utente non è autorizzato ad accedere a SIFT OS.",
            "SESSION_INVALID": "La sessione non è valida o è scaduta.",
            "CSRF_INVALID": "Il token CSRF non è valido.",
        }
        super().__init__(
            status_code=status_code,
            code=code,
            message=messages[code],
        )


async def exchange_platform_ticket(ticket: str, settings: Settings) -> str:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{str(settings.sift_platform_public_url).rstrip('/')}/api/v1/sso/exchange",
                json={
                    "ticket": ticket,
                    "audience": settings.sift_platform_sso_audience,
                },
            )
        if response.status_code != 200:
            raise AuthFailure("SSO_TICKET_INVALID")
        return PlatformExchange.model_validate(response.json()).access_token
    except AuthFailure:
        raise
    except (httpx.HTTPError, ValueError, ValidationError):
        raise AuthFailure("SSO_TICKET_INVALID") from None


def verify_platform_assertion(
    token: str,
    jwks: PyJWKClient,
    settings: Settings,
) -> PlatformClaims:
    try:
        signing_key = jwks.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.sift_platform_sso_audience,
            issuer=str(settings.sift_platform_sso_issuer).rstrip("/"),
            options={
                "require": [
                    "iss",
                    "aud",
                    "sub",
                    "exp",
                    "iat",
                    "jti",
                    "product_id",
                    "entitlement_id",
                ]
            },
        )
        return PlatformClaims.model_validate(payload)
    except (jwt.PyJWTError, ValueError, ValidationError):
        raise AuthFailure("SSO_ASSERTION_INVALID") from None


def platform_jwks(settings: Settings) -> PyJWKClient:
    return PyJWKClient(
        str(settings.sift_platform_jwks_url),
        cache_jwk_set=True,
        lifespan=300,
        timeout=5,
    )
