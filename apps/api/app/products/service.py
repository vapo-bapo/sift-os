from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.products.credentials import hash_service_token, issue_service_token, parse_service_token
from app.products.models import Product, ProductEvent, ProductRun, ProductServiceCredential


def get_product(db: Session, product_id: UUID) -> Product:
    product = db.scalar(
        select(Product).where(
            Product.id == product_id, Product.active.is_(True), Product.archived_at.is_(None)
        )
    )
    if product is None:
        raise ApiError(status_code=404, code="PRODUCT_NOT_FOUND", message="Prodotto non trovato.")
    return product


def list_products(db: Session) -> list[Product]:
    return list(
        db.scalars(
            select(Product)
            .where(Product.active.is_(True), Product.archived_at.is_(None))
            .order_by(Product.code)
        )
    )


def create_credential(
    db: Session,
    *,
    product: Product,
    name: str,
    actor_id: UUID,
    expires_at: datetime | None = None,
    rotated_from_id: UUID | None = None,
) -> tuple[ProductServiceCredential, str]:
    credential_id = uuid4()
    token = issue_service_token(credential_id)
    credential = ProductServiceCredential(
        id=credential_id,
        product_id=product.id,
        name=name,
        token_digest=hash_service_token(token),
        created_by=actor_id,
        expires_at=expires_at,
        rotated_from_id=rotated_from_id,
    )
    db.add(credential)
    db.flush()
    return credential, token


def revoke_credential(
    db: Session, *, product_id: UUID, credential_id: UUID, actor_id: UUID
) -> ProductServiceCredential:
    credential = db.scalar(
        select(ProductServiceCredential)
        .where(
            ProductServiceCredential.id == credential_id,
            ProductServiceCredential.product_id == product_id,
        )
        .with_for_update()
    )
    if credential is None:
        raise ApiError(
            status_code=404, code="CREDENTIAL_NOT_FOUND", message="Credenziale non trovata."
        )
    if credential.revoked_at is None:
        credential.revoked_at = datetime.now(UTC)
        credential.revoked_by = actor_id
        db.flush()
    return credential


def rotate_credential(
    db: Session, *, product: Product, credential_id: UUID, actor_id: UUID
) -> tuple[ProductServiceCredential, str]:
    active = db.scalar(
        select(ProductServiceCredential)
        .where(
            ProductServiceCredential.id == credential_id,
            ProductServiceCredential.product_id == product.id,
        )
        .with_for_update()
    )
    if active is None:
        raise ApiError(
            status_code=404, code="CREDENTIAL_NOT_FOUND", message="Credenziale non trovata."
        )
    if active.revoked_at is not None:
        raise ApiError(
            status_code=409,
            code="CREDENTIAL_ALREADY_REVOKED",
            message="La credenziale è già stata revocata.",
        )
    previous = revoke_credential(
        db, product_id=product.id, credential_id=credential_id, actor_id=actor_id
    )
    return create_credential(
        db,
        product=product,
        name=previous.name,
        actor_id=actor_id,
        expires_at=previous.expires_at,
        rotated_from_id=previous.id,
    )


def authenticate_service_token(db: Session, token: str) -> ProductServiceCredential:
    try:
        credential_id = parse_service_token(token)
    except ValueError as exc:
        raise ApiError(
            status_code=401,
            code="SERVICE_CREDENTIAL_INVALID",
            message="Credenziale di servizio non valida.",
        ) from exc
    credential = db.scalar(
        select(ProductServiceCredential).where(ProductServiceCredential.id == credential_id)
    )
    now = datetime.now(UTC)
    if (
        credential is None
        or credential.revoked_at is not None
        or (credential.expires_at is not None and credential.expires_at <= now)
        or not secrets_compare(credential.token_digest, hash_service_token(token))
    ):
        raise ApiError(
            status_code=401,
            code="SERVICE_CREDENTIAL_INVALID",
            message="Credenziale di servizio non valida.",
        )
    credential.last_used_at = now
    return credential


def secrets_compare(left: str, right: str) -> bool:
    import hmac

    return hmac.compare_digest(left, right)


def product_metrics(db: Session) -> list[dict[str, object]]:
    run_stats = (
        select(
            ProductRun.product_id.label("product_id"),
            func.count(ProductRun.id).label("runs_total"),
            func.count(ProductRun.id).filter(ProductRun.status == "running").label("runs_running"),
            func.count(ProductRun.id)
            .filter(ProductRun.status == "succeeded")
            .label("runs_succeeded"),
            func.count(ProductRun.id).filter(ProductRun.status == "failed").label("runs_failed"),
        )
        .group_by(ProductRun.product_id)
        .subquery()
    )
    event_stats = (
        select(
            ProductEvent.product_id.label("product_id"),
            func.count(ProductEvent.id).label("events_total"),
            func.sum(ProductEvent.cost_cents).label("cost_cents"),
            func.sum(ProductEvent.units).label("units"),
        )
        .group_by(ProductEvent.product_id)
        .subquery()
    )
    rows = db.execute(
        select(
            Product.id,
            Product.code,
            func.coalesce(run_stats.c.runs_total, 0),
            func.coalesce(run_stats.c.runs_running, 0),
            func.coalesce(run_stats.c.runs_succeeded, 0),
            func.coalesce(run_stats.c.runs_failed, 0),
            func.coalesce(event_stats.c.events_total, 0),
            func.coalesce(event_stats.c.cost_cents, 0),
            func.coalesce(event_stats.c.units, 0),
        )
        .outerjoin(run_stats, run_stats.c.product_id == Product.id)
        .outerjoin(event_stats, event_stats.c.product_id == Product.id)
        .where(Product.active.is_(True), Product.archived_at.is_(None))
        .order_by(Product.code)
    ).all()
    return [
        {
            "product_id": row[0],
            "code": row[1],
            "runs_total": row[2],
            "runs_running": row[3],
            "runs_succeeded": row[4],
            "runs_failed": row[5],
            "events_total": row[6],
            "cost_cents": row[7],
            "units": row[8],
        }
        for row in rows
    ]


def product_metric(db: Session, product_id: UUID) -> dict[str, object]:
    get_product(db, product_id)
    metric = next((item for item in product_metrics(db) if item["product_id"] == product_id), None)
    if metric is None:
        raise RuntimeError("active product metric row missing")
    return metric
