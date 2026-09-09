from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select, true
from sqlalchemy.orm import Session

from app.company.models import Task
from app.crm.models import CrmAccount, CrmContact, CrmOpportunity
from app.db.session import get_db
from app.partners.models import Partner
from app.staff.dependencies import CurrentStaff, get_current_staff
from app.staff.permissions import Permission

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
def global_search(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentStaff, Depends(get_current_staff)],
    q: str = Query(min_length=2, max_length=120),
) -> dict[str, list[dict[str, Any]]]:
    term = f"%{q.strip()}%"
    result: dict[str, list[dict[str, Any]]] = {
        "accounts": [],
        "contacts": [],
        "opportunities": [],
        "partners": [],
        "tasks": [],
    }
    if current.permissions & {Permission.SALES_READ_ALL, Permission.SALES_READ_OWN}:
        account_scope = (
            true()
            if Permission.SALES_READ_ALL in current.permissions
            else CrmAccount.owner_id == current.staff.id
        )
        accounts = db.scalars(
            select(CrmAccount)
            .where(
                account_scope,
                CrmAccount.archived_at.is_(None),
                or_(CrmAccount.name.ilike(term), CrmAccount.domain.ilike(term)),
            )
            .limit(8)
        )
        result["accounts"] = [
            {"id": str(item.id), "label": item.name, "detail": item.domain, "type": "account"}
            for item in accounts
        ]
        contacts = db.scalars(
            select(CrmContact)
            .join(CrmAccount, CrmAccount.id == CrmContact.account_id)
            .where(
                account_scope,
                or_(
                    CrmContact.first_name.ilike(term),
                    CrmContact.last_name.ilike(term),
                    CrmContact.email.ilike(term),
                ),
            )
            .limit(8)
        )
        result["contacts"] = [
            {
                "id": str(item.id),
                "label": f"{item.first_name} {item.last_name}",
                "detail": item.email,
                "type": "contact",
            }
            for item in contacts
        ]
        opportunities = db.scalars(
            select(CrmOpportunity)
            .join(CrmAccount, CrmAccount.id == CrmOpportunity.account_id)
            .where(account_scope, CrmAccount.name.ilike(term))
            .limit(8)
        )
        result["opportunities"] = [
            {
                "id": str(item.id),
                "label": str(item.account_id),
                "detail": item.stage.value,
                "type": "opportunity",
            }
            for item in opportunities
        ]
    if current.permissions & {Permission.PARTNER_READ, Permission.PARTNER_READ_ASSIGNED}:
        partner_scope = (
            true()
            if Permission.PARTNER_READ in current.permissions
            else Partner.owner_staff_id == current.staff.id
        )
        partners = db.scalars(
            select(Partner)
            .where(partner_scope, Partner.archived_at.is_(None), Partner.name.ilike(term))
            .limit(8)
        )
        result["partners"] = [
            {"id": str(item.id), "label": item.name, "detail": item.status.value, "type": "partner"}
            for item in partners
        ]
    task_scope = (
        true()
        if Permission.TASK_WRITE in current.permissions
        else Task.owner_id == current.staff.id
    )
    tasks = db.scalars(
        select(Task).where(task_scope, Task.archived_at.is_(None), Task.title.ilike(term)).limit(8)
    )
    result["tasks"] = [
        {"id": str(item.id), "label": item.title, "detail": item.status.value, "type": "task"}
        for item in tasks
    ]
    return result
