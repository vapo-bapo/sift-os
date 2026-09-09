from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditResult
from app.audit.service import record_audit_log
from app.db.session import get_db
from app.products.models import Product, ProductServiceCredential
from app.products.schemas import (
    CredentialCreate,
    CredentialIssued,
    CredentialRead,
    ProductMetricRead,
    ProductRead,
)
from app.products.service import (
    create_credential,
    get_product,
    list_products,
    product_metric,
    product_metrics,
    revoke_credential,
    rotate_credential,
)
from app.staff.dependencies import CurrentStaff, require_csrf, require_permission
from app.staff.permissions import Permission

router = APIRouter(prefix="/api/products", tags=["products"])

ProductReader = Annotated[CurrentStaff, Depends(require_permission(Permission.PRODUCT_READ))]
ProductAdmin = Annotated[CurrentStaff, Depends(require_permission(Permission.INTEGRATION_MANAGE))]


def _audit(
    db: Session,
    request: Request,
    current: CurrentStaff,
    *,
    action: str,
    entity_id: UUID,
    new: dict[str, object],
) -> None:
    record_audit_log(
        db,
        actor_staff_id=current.staff.id,
        action=action,
        entity_type="product_service_credential",
        entity_id=entity_id,
        previous=None,
        new=new,
        request_id=request.state.request_id,
        ip_address=request.client.host if request.client else None,
        user_agent_summary=request.headers.get("user-agent", "")[:256] or None,
        result=AuditResult.SUCCESS,
    )


@router.get("", response_model=list[ProductRead])
def products(db: Annotated[Session, Depends(get_db)], current: ProductReader) -> list[Product]:
    del current
    return list_products(db)


@router.get("/metrics", response_model=list[ProductMetricRead])
def metrics(
    db: Annotated[Session, Depends(get_db)], current: ProductReader
) -> list[dict[str, object]]:
    del current
    return product_metrics(db)


@router.get("/{product_id}/metrics", response_model=ProductMetricRead)
def metric(
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current: ProductReader,
) -> dict[str, object]:
    del current
    return product_metric(db, product_id)


@router.get("/{product_id}/credentials", response_model=list[CredentialRead])
def credentials(
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current: ProductAdmin,
) -> list[ProductServiceCredential]:
    del current
    get_product(db, product_id)
    return list(
        db.scalars(
            select(ProductServiceCredential)
            .where(ProductServiceCredential.product_id == product_id)
            .order_by(ProductServiceCredential.created_at.desc())
        )
    )


@router.post("/{product_id}/credentials", response_model=CredentialIssued, status_code=201)
def add_credential(
    product_id: UUID,
    payload: CredentialCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current: ProductAdmin,
    csrf_current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> CredentialIssued:
    del csrf_current
    product = get_product(db, product_id)
    credential, token = create_credential(
        db,
        product=product,
        name=payload.name,
        actor_id=current.staff.id,
        expires_at=payload.expires_at,
    )
    _audit(
        db,
        request,
        current,
        action="product.credential.created",
        entity_id=credential.id,
        new={"product_id": str(product.id), "name": credential.name},
    )
    db.commit()
    return CredentialIssued(
        id=credential.id,
        product_id=credential.product_id,
        name=credential.name,
        token=token,
        created_at=credential.created_at,
        expires_at=credential.expires_at,
    )


@router.post(
    "/{product_id}/credentials/{credential_id}/rotate",
    response_model=CredentialIssued,
    status_code=201,
)
def rotate(
    product_id: UUID,
    credential_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current: ProductAdmin,
    csrf_current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> CredentialIssued:
    del csrf_current
    product = get_product(db, product_id)
    credential, token = rotate_credential(
        db, product=product, credential_id=credential_id, actor_id=current.staff.id
    )
    _audit(
        db,
        request,
        current,
        action="product.credential.rotated",
        entity_id=credential.id,
        new={"product_id": str(product.id), "rotated_from_id": str(credential_id)},
    )
    db.commit()
    return CredentialIssued(
        id=credential.id,
        product_id=credential.product_id,
        name=credential.name,
        token=token,
        created_at=credential.created_at,
        expires_at=credential.expires_at,
    )


@router.post("/{product_id}/credentials/{credential_id}/revoke", response_model=CredentialRead)
def revoke(
    product_id: UUID,
    credential_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current: ProductAdmin,
    csrf_current: Annotated[CurrentStaff, Depends(require_csrf)],
) -> ProductServiceCredential:
    del csrf_current
    get_product(db, product_id)
    credential = revoke_credential(
        db, product_id=product_id, credential_id=credential_id, actor_id=current.staff.id
    )
    _audit(
        db,
        request,
        current,
        action="product.credential.revoked",
        entity_id=credential.id,
        new={"product_id": str(product_id), "revoked": True},
    )
    db.commit()
    return credential
