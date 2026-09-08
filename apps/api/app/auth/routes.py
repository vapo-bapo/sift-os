from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.orm import Session

from app.audit.models import AuditResult
from app.audit.service import record_audit_log
from app.auth.schemas import SSOExchangeRequest
from app.auth.service import create_local_session, revoke_local_session
from app.auth.sso import AuthFailure, exchange_platform_ticket, verify_platform_assertion
from app.core.config import Settings
from app.db.session import get_db

router = APIRouter(prefix="/api", tags=["auth"])


def _set_auth_cookies(
    response: Response,
    *,
    raw_session: str,
    raw_csrf: str,
    settings: Settings,
) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        raw_session,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
        path="/",
        domain=settings.cookie_domain,
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        raw_csrf,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
        path="/",
        domain=settings.cookie_domain,
    )


def _clear_auth_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        settings.csrf_cookie_name,
        path="/",
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=False,
        samesite="lax",
    )


@router.post("/auth/sso/exchange", status_code=status.HTTP_204_NO_CONTENT)
async def exchange_sso(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    settings: Settings = request.app.state.settings
    try:
        payload = SSOExchangeRequest.model_validate(await request.json())
    except ValueError:
        raise AuthFailure("SSO_REQUEST_INVALID", status_code=422) from None
    assertion = await exchange_platform_ticket(payload.ticket, settings)
    claims = verify_platform_assertion(assertion, request.app.state.platform_jwks, settings)
    local_session = create_local_session(db, claims=claims, settings=settings)
    db.commit()
    request.state.platform_user_id = claims.sub
    _set_auth_cookies(
        response,
        raw_session=local_session.raw_session,
        raw_csrf=local_session.raw_csrf,
        settings=settings,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    settings: Settings = request.app.state.settings
    user_session = revoke_local_session(
        db,
        raw_session=request.cookies.get(settings.session_cookie_name),
        csrf_cookie=request.cookies.get(settings.csrf_cookie_name),
        csrf_header=csrf_header,
        settings=settings,
    )
    record_audit_log(
        db,
        actor_staff_id=user_session.staff_member_id,
        action="auth.logout",
        entity_type="user_session",
        entity_id=user_session.id,
        previous={"revoked": False},
        new={"revoked": True},
        request_id=request.state.request_id,
        ip_address=request.client.host if request.client is not None else None,
        user_agent_summary=request.headers.get("user-agent", "")[:256] or None,
        result=AuditResult.SUCCESS,
    )
    db.commit()
    request.state.platform_user_id = user_session.staff_member_id
    _clear_auth_cookies(response, settings)
