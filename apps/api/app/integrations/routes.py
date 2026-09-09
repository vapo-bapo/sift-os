from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.session import get_db
from app.integrations.schemas import ProductEventAccepted, ProductEventIn
from app.integrations.service import ingest_product_event
from app.products.service import authenticate_service_token

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.post("/events", response_model=ProductEventAccepted, status_code=202)
def ingest_event(
    payload: ProductEventIn,
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> ProductEventAccepted:
    if authorization is None or not authorization.startswith("Bearer "):
        raise ApiError(
            status_code=401,
            code="SERVICE_CREDENTIAL_INVALID",
            message="Credenziale di servizio non valida.",
        )
    credential = authenticate_service_token(db, authorization.removeprefix("Bearer "))
    result = ingest_product_event(db, product_id=credential.product_id, payload=payload)
    db.commit()
    return result
