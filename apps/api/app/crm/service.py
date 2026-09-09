from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.errors import ApiError
from app.crm.csv_import import parse_account_csv
from app.crm.models import (
    AccountStatus,
    AccountType,
    ActivityType,
    CrmAccount,
    CrmActivity,
    CrmCaseStudyMetrics,
    CrmContact,
    CrmOpportunity,
    OpportunityStage,
    OpportunityStageHistory,
    OpportunityStatus,
)
from app.crm.normalization import normalize_domain, normalize_email, normalize_name, normalize_phone
from app.crm.schemas import (
    AccountCreate,
    AccountCsvImportResponse,
    AccountUpdate,
    ActivityCreate,
    ActivityUpdate,
    CaseStudyMetricsUpdate,
    ContactCreate,
    ContactUpdate,
    CsvParseResult,
    LeaderboardRow,
    MyDayResponse,
    OpportunityCreate,
    OpportunityUpdate,
    PipelineStageSummary,
)
from app.staff.dependencies import CurrentStaff
from app.staff.models import StaffMember
from app.staff.permissions import Permission

FOLLOW_UP_INVALID_MESSAGE = (
    "Per creare il follow-up servono completamento e data della prossima azione."
)


def _not_found(entity: str) -> ApiError:
    return ApiError(
        status_code=404, code=f"CRM_{entity.upper()}_NOT_FOUND", message="Record CRM non trovato."
    )


def _can_read_all(actor: CurrentStaff) -> bool:
    return Permission.SALES_READ_ALL in actor.permissions


def _can_write_all(actor: CurrentStaff) -> bool:
    return Permission.SALES_WRITE_ALL in actor.permissions


def _ensure_sales_read(actor: CurrentStaff) -> None:
    if not ({Permission.SALES_READ_ALL, Permission.SALES_READ_OWN} & actor.permissions):
        raise ApiError(
            status_code=403, code="PERMISSION_DENIED", message="Non hai i permessi necessari."
        )


def _ensure_sales_write(actor: CurrentStaff) -> None:
    if not ({Permission.SALES_WRITE_ALL, Permission.SALES_WRITE_OWN} & actor.permissions):
        raise ApiError(
            status_code=403, code="PERMISSION_DENIED", message="Non hai i permessi necessari."
        )


def _ensure_owner_access(actor: CurrentStaff, owner_id: UUID, *, write: bool = False) -> None:
    allowed_all = _can_write_all(actor) if write else _can_read_all(actor)
    if not allowed_all and owner_id != actor.staff.id:
        raise ApiError(
            status_code=403, code="CRM_RECORD_FORBIDDEN", message="Record CRM non accessibile."
        )


def _resolve_owner(db: Session, actor: CurrentStaff, requested: UUID | None) -> UUID:
    owner_id = requested or actor.staff.id
    if owner_id != actor.staff.id and Permission.SALES_ASSIGN not in actor.permissions:
        raise ApiError(
            status_code=403,
            code="PERMISSION_DENIED",
            message="Non puoi assegnare record ad altri utenti.",
        )
    owner = db.get(StaffMember, owner_id)
    if owner is None or not owner.active:
        raise ApiError(
            status_code=422,
            code="CRM_OWNER_INVALID",
            message="Il responsabile selezionato non è attivo.",
        )
    return owner_id


def _paginate[ModelT](
    db: Session, query: Select[tuple[ModelT]], *, page: int, page_size: int
) -> tuple[list[ModelT], int]:
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    items = list(db.scalars(query.offset((page - 1) * page_size).limit(page_size)))
    return items, total


def create_account(db: Session, actor: CurrentStaff, payload: AccountCreate) -> CrmAccount:
    _ensure_sales_write(actor)
    normalized_domain = normalize_domain(payload.domain)
    if normalized_domain is not None and db.scalar(
        select(CrmAccount.id).where(
            CrmAccount.normalized_domain == normalized_domain,
            CrmAccount.archived_at.is_(None),
        )
    ):
        raise ApiError(
            status_code=409,
            code="CRM_ACCOUNT_DUPLICATE",
            message="Esiste già un account con questo dominio.",
        )
    data = payload.model_dump(exclude={"owner_id"})
    account = CrmAccount(
        **data,
        owner_id=_resolve_owner(db, actor, payload.owner_id),
        normalized_domain=normalized_domain,
    )
    db.add(account)
    return account


def preview_account_import(db: Session, actor: CurrentStaff, csv_content: str) -> CsvParseResult:
    _ensure_sales_write(actor)
    preview = parse_account_csv(csv_content)
    domains = {row.normalized_domain for row in preview.rows if row.normalized_domain is not None}
    if domains:
        existing_rows = db.execute(
            select(CrmAccount.normalized_domain, CrmAccount.id).where(
                CrmAccount.normalized_domain.in_(domains),
                CrmAccount.archived_at.is_(None),
            )
        ).all()
        existing: dict[str, UUID] = {
            domain: account_id for domain, account_id in existing_rows if domain is not None
        }
        for row in preview.rows:
            if row.normalized_domain in existing:
                row.valid = False
                row.duplicate_account_id = existing[row.normalized_domain]
                row.errors.append("domain already exists")
    preview.valid_rows = sum(row.valid for row in preview.rows)
    preview.invalid_rows = sum(not row.valid for row in preview.rows)
    return preview


def import_accounts(
    db: Session,
    actor: CurrentStaff,
    csv_content: str,
    *,
    confirmed: bool,
) -> AccountCsvImportResponse:
    if not confirmed:
        raise ApiError(
            status_code=422,
            code="CRM_IMPORT_CONFIRMATION_REQUIRED",
            message="Conferma l'importazione dopo aver controllato l'anteprima.",
        )
    preview = preview_account_import(db, actor, csv_content)
    if preview.file_errors or preview.invalid_rows:
        raise ApiError(
            status_code=422,
            code="CRM_IMPORT_INVALID",
            message="Correggi gli errori del CSV prima di importare.",
            details=preview.model_dump(mode="json"),
        )
    accounts = [
        create_account(db, actor, AccountCreate.model_validate(row.values)) for row in preview.rows
    ]
    db.flush()
    return AccountCsvImportResponse(
        imported=len(accounts), account_ids=[account.id for account in accounts]
    )


def seed_case_studies(db: Session, actor: CurrentStaff) -> list[CrmAccount]:
    _ensure_sales_write(actor)
    if not _can_write_all(actor):
        raise ApiError(
            status_code=403,
            code="PERMISSION_DENIED",
            message="Solo la leadership può inizializzare i case study.",
        )
    accounts: list[CrmAccount] = []
    for name in ("Stral", "Auris"):
        account = db.scalar(
            select(CrmAccount).where(
                func.lower(CrmAccount.name) == name.casefold(),
                CrmAccount.account_type == AccountType.CASE_STUDY,
            )
        )
        if account is None:
            account = create_account(
                db,
                actor,
                AccountCreate(
                    name=name,
                    account_type=AccountType.CASE_STUDY,
                    owner_id=actor.staff.id,
                ),
            )
            db.flush()
        accounts.append(account)
    return accounts


def upsert_case_study_metrics(
    db: Session,
    actor: CurrentStaff,
    account_id: UUID,
    payload: CaseStudyMetricsUpdate,
) -> CrmCaseStudyMetrics:
    account = get_account(db, actor, account_id, write=True)
    if account.account_type != AccountType.CASE_STUDY:
        raise ApiError(
            status_code=422,
            code="CRM_CASE_STUDY_REQUIRED",
            message="Le metriche possono essere associate solo a un case study.",
        )
    metrics = db.scalar(
        select(CrmCaseStudyMetrics).where(CrmCaseStudyMetrics.account_id == account_id)
    )
    if metrics is None:
        metrics = CrmCaseStudyMetrics(account_id=account_id)
        db.add(metrics)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(metrics, key, value)
    return metrics


def get_case_study_metrics(
    db: Session, actor: CurrentStaff, account_id: UUID
) -> CrmCaseStudyMetrics:
    account = get_account(db, actor, account_id)
    if account.account_type != AccountType.CASE_STUDY:
        raise _not_found("case_study_metrics")
    metrics = db.scalar(
        select(CrmCaseStudyMetrics).where(CrmCaseStudyMetrics.account_id == account_id)
    )
    if metrics is None:
        raise _not_found("case_study_metrics")
    return metrics


def list_accounts(
    db: Session,
    actor: CurrentStaff,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
    owner_id: UUID | None = None,
    account_type: AccountType | None = None,
    status: AccountStatus | None = None,
    include_archived: bool = False,
) -> tuple[list[CrmAccount], int]:
    _ensure_sales_read(actor)
    query = select(CrmAccount)
    if not include_archived:
        query = query.where(CrmAccount.archived_at.is_(None))
    if not _can_read_all(actor):
        query = query.where(CrmAccount.owner_id == actor.staff.id)
    elif owner_id is not None:
        query = query.where(CrmAccount.owner_id == owner_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(CrmAccount.name.ilike(pattern), CrmAccount.domain.ilike(pattern)))
    if account_type is not None:
        query = query.where(CrmAccount.account_type == account_type)
    if status is not None:
        query = query.where(CrmAccount.status == status)
    return _paginate(
        db, query.order_by(CrmAccount.updated_at.desc()), page=page, page_size=page_size
    )


def get_account(
    db: Session, actor: CurrentStaff, account_id: UUID, *, write: bool = False
) -> CrmAccount:
    _ensure_sales_write(actor) if write else _ensure_sales_read(actor)
    account = db.get(CrmAccount, account_id)
    if account is None:
        raise _not_found("account")
    _ensure_owner_access(actor, account.owner_id, write=write)
    return account


def update_account(
    db: Session, actor: CurrentStaff, account_id: UUID, payload: AccountUpdate
) -> CrmAccount:
    account = get_account(db, actor, account_id, write=True)
    changes = payload.model_dump(exclude_unset=True)
    if "owner_id" in changes:
        changes["owner_id"] = _resolve_owner(db, actor, changes["owner_id"])
    if "domain" in changes:
        normalized = normalize_domain(changes["domain"])
        duplicate = None
        if normalized is not None:
            duplicate = db.scalar(
                select(CrmAccount.id).where(
                    CrmAccount.normalized_domain == normalized,
                    CrmAccount.id != account.id,
                    CrmAccount.archived_at.is_(None),
                )
            )
        if duplicate:
            raise ApiError(
                status_code=409,
                code="CRM_ACCOUNT_DUPLICATE",
                message="Esiste già un account con questo dominio.",
            )
        changes["normalized_domain"] = normalized
    for key, value in changes.items():
        setattr(account, key, value)
    return account


def archive_account(db: Session, actor: CurrentStaff, account_id: UUID) -> CrmAccount:
    account = get_account(db, actor, account_id, write=True)
    if account.archived_at is None:
        account.archived_at = datetime.now(UTC)
    return account


def _ensure_account_access(
    db: Session, actor: CurrentStaff, account_id: UUID, *, write: bool
) -> CrmAccount:
    return get_account(db, actor, account_id, write=write)


def create_contact(db: Session, actor: CurrentStaff, payload: ContactCreate) -> CrmContact:
    _ensure_sales_write(actor)
    _ensure_account_access(db, actor, payload.account_id, write=True)
    email = normalize_email(payload.email)
    phone = normalize_phone(payload.phone)
    name = normalize_name(f"{payload.first_name} {payload.last_name}")
    duplicate_filters: list[ColumnElement[bool]] = [
        (CrmContact.account_id == payload.account_id) & (CrmContact.normalized_name == name),
    ]
    if email is not None:
        duplicate_filters.append(CrmContact.normalized_email == email)
    if phone is not None:
        duplicate_filters.append(
            (CrmContact.account_id == payload.account_id) & (CrmContact.normalized_phone == phone)
        )
    if db.scalar(select(CrmContact.id).where(or_(*duplicate_filters))):
        raise ApiError(
            status_code=409,
            code="CRM_CONTACT_DUPLICATE",
            message="Il contatto sembra già presente.",
        )
    contact = CrmContact(
        **payload.model_dump(),
        normalized_name=name,
        normalized_email=email,
        normalized_phone=phone,
    )
    db.add(contact)
    return contact


def list_contacts(
    db: Session,
    actor: CurrentStaff,
    *,
    page: int,
    page_size: int,
    account_id: UUID | None = None,
    search: str | None = None,
) -> tuple[list[CrmContact], int]:
    _ensure_sales_read(actor)
    query = select(CrmContact).join(CrmAccount)
    if not _can_read_all(actor):
        query = query.where(CrmAccount.owner_id == actor.staff.id)
    if account_id is not None:
        query = query.where(CrmContact.account_id == account_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(CrmContact.normalized_name.ilike(pattern), CrmContact.email.ilike(pattern))
        )
    return _paginate(
        db, query.order_by(CrmContact.updated_at.desc()), page=page, page_size=page_size
    )


def update_contact(
    db: Session, actor: CurrentStaff, contact_id: UUID, payload: ContactUpdate
) -> CrmContact:
    contact = db.get(CrmContact, contact_id)
    if contact is None:
        raise _not_found("contact")
    _ensure_account_access(db, actor, contact.account_id, write=True)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(contact, key, value)
    if {"first_name", "last_name"} & changes.keys():
        contact.normalized_name = normalize_name(f"{contact.first_name} {contact.last_name}")
    if "email" in changes:
        contact.normalized_email = normalize_email(contact.email)
    if "phone" in changes:
        contact.normalized_phone = normalize_phone(contact.phone)
    duplicate_filters: list[ColumnElement[bool]] = [
        (CrmContact.account_id == contact.account_id)
        & (CrmContact.normalized_name == contact.normalized_name)
    ]
    if contact.normalized_email is not None:
        duplicate_filters.append(CrmContact.normalized_email == contact.normalized_email)
    if contact.normalized_phone is not None:
        duplicate_filters.append(
            (CrmContact.account_id == contact.account_id)
            & (CrmContact.normalized_phone == contact.normalized_phone)
        )
    duplicate = db.scalar(
        select(CrmContact.id).where(
            CrmContact.id != contact.id,
            or_(*duplicate_filters),
        )
    )
    if duplicate:
        raise ApiError(
            status_code=409,
            code="CRM_CONTACT_DUPLICATE",
            message="Il contatto sembra già presente.",
        )
    return contact


def create_opportunity(
    db: Session, actor: CurrentStaff, payload: OpportunityCreate
) -> CrmOpportunity:
    _ensure_sales_write(actor)
    _ensure_account_access(db, actor, payload.account_id, write=True)
    if payload.primary_contact_id is not None:
        contact = db.get(CrmContact, payload.primary_contact_id)
        if contact is None or contact.account_id != payload.account_id:
            raise ApiError(
                status_code=422,
                code="CRM_CONTACT_INVALID",
                message="Contatto non valido per questo account.",
            )
    owner_id = _resolve_owner(db, actor, payload.owner_id)
    data = payload.model_dump(exclude={"owner_id", "weighted_value_cents"})
    opportunity = CrmOpportunity(
        **data,
        owner_id=owner_id,
        weighted_value_cents=payload.weighted_value_cents,
    )
    db.add(opportunity)
    db.flush()
    db.add(
        OpportunityStageHistory(
            opportunity_id=opportunity.id,
            previous_stage=None,
            new_stage=opportunity.stage,
            changed_by=actor.staff.id,
        )
    )
    return opportunity


def get_opportunity(
    db: Session, actor: CurrentStaff, opportunity_id: UUID, *, write: bool = False
) -> CrmOpportunity:
    _ensure_sales_write(actor) if write else _ensure_sales_read(actor)
    opportunity = db.get(CrmOpportunity, opportunity_id)
    if opportunity is None:
        raise _not_found("opportunity")
    _ensure_owner_access(actor, opportunity.owner_id, write=write)
    return opportunity


def list_opportunities(
    db: Session,
    actor: CurrentStaff,
    *,
    page: int,
    page_size: int,
    owner_id: UUID | None = None,
    stage: OpportunityStage | None = None,
    search: str | None = None,
    stale_days: int | None = None,
) -> tuple[list[CrmOpportunity], int]:
    _ensure_sales_read(actor)
    query = select(CrmOpportunity).join(CrmAccount)
    if not _can_read_all(actor):
        query = query.where(CrmOpportunity.owner_id == actor.staff.id)
    elif owner_id is not None:
        query = query.where(CrmOpportunity.owner_id == owner_id)
    if stage is not None:
        query = query.where(CrmOpportunity.stage == stage)
    if search:
        query = query.where(CrmAccount.name.ilike(f"%{search.strip()}%"))
    if stale_days is not None:
        query = query.where(
            CrmOpportunity.updated_at < datetime.now(UTC) - timedelta(days=stale_days)
        )
    return _paginate(
        db, query.order_by(CrmOpportunity.updated_at.desc()), page=page, page_size=page_size
    )


def _recalculate(opportunity: CrmOpportunity) -> None:
    opportunity.weighted_value_cents = (
        opportunity.estimated_value_cents * opportunity.probability // 100
    )


def update_opportunity(
    db: Session, actor: CurrentStaff, opportunity_id: UUID, payload: OpportunityUpdate
) -> CrmOpportunity:
    opportunity = get_opportunity(db, actor, opportunity_id, write=True)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(opportunity, key, value)
    _recalculate(opportunity)
    return opportunity


def change_opportunity_stage(
    db: Session,
    actor: CurrentStaff,
    opportunity_id: UUID,
    stage: OpportunityStage,
    lost_reason: str | None = None,
) -> CrmOpportunity:
    opportunity = get_opportunity(db, actor, opportunity_id, write=True)
    previous = opportunity.stage
    if stage == previous:
        return opportunity
    opportunity.stage = stage
    opportunity.status = {
        OpportunityStage.WON: OpportunityStatus.WON,
        OpportunityStage.LOST: OpportunityStatus.LOST,
        OpportunityStage.DISQUALIFIED: OpportunityStatus.DISQUALIFIED,
    }.get(stage, OpportunityStatus.OPEN)
    opportunity.won_at = datetime.now(UTC) if stage == OpportunityStage.WON else None
    opportunity.lost_reason = (
        lost_reason if stage in {OpportunityStage.LOST, OpportunityStage.DISQUALIFIED} else None
    )
    db.add(
        OpportunityStageHistory(
            opportunity_id=opportunity.id,
            previous_stage=previous,
            new_stage=stage,
            changed_by=actor.staff.id,
        )
    )
    return opportunity


def assign_opportunity(
    db: Session, actor: CurrentStaff, opportunity_id: UUID, owner_id: UUID
) -> CrmOpportunity:
    if Permission.SALES_ASSIGN not in actor.permissions:
        raise ApiError(
            status_code=403, code="PERMISSION_DENIED", message="Non puoi assegnare opportunità."
        )
    opportunity = get_opportunity(db, actor, opportunity_id, write=True)
    opportunity.owner_id = _resolve_owner(db, actor, owner_id)
    return opportunity


def create_activity(db: Session, actor: CurrentStaff, payload: ActivityCreate) -> CrmActivity:
    _ensure_sales_write(actor)
    if payload.account_id is None and payload.contact_id is None and payload.opportunity_id is None:
        raise ApiError(
            status_code=422,
            code="CRM_ACTIVITY_SUBJECT_REQUIRED",
            message="L'attività deve riferirsi a un record CRM.",
        )
    subject_account_id = payload.account_id
    if subject_account_id is not None:
        _ensure_account_access(db, actor, subject_account_id, write=True)
    if payload.contact_id is not None:
        contact = db.get(CrmContact, payload.contact_id)
        if contact is None:
            raise _not_found("contact")
        _ensure_account_access(db, actor, contact.account_id, write=True)
        if subject_account_id is not None and contact.account_id != subject_account_id:
            raise ApiError(
                status_code=422,
                code="CRM_ACTIVITY_SUBJECT_MISMATCH",
                message="I record collegati all'attività non appartengono allo stesso account.",
            )
        subject_account_id = contact.account_id
    if payload.opportunity_id is not None:
        opportunity = get_opportunity(db, actor, payload.opportunity_id, write=True)
        if subject_account_id is not None and opportunity.account_id != subject_account_id:
            raise ApiError(
                status_code=422,
                code="CRM_ACTIVITY_SUBJECT_MISMATCH",
                message="I record collegati all'attività non appartengono allo stesso account.",
            )
        subject_account_id = opportunity.account_id
    owner_id = _resolve_owner(db, actor, payload.owner_id)
    data = payload.model_dump(exclude={"owner_id", "create_follow_up"})
    data["account_id"] = subject_account_id
    activity = CrmActivity(**data, owner_id=owner_id)
    db.add(activity)
    if payload.create_follow_up:
        if payload.completed_at is None or payload.next_action_at is None:
            raise ApiError(
                status_code=422,
                code="CRM_FOLLOW_UP_INVALID",
                message=FOLLOW_UP_INVALID_MESSAGE,
            )
        db.add(
            CrmActivity(
                account_id=payload.account_id,
                contact_id=payload.contact_id,
                opportunity_id=payload.opportunity_id,
                owner_id=owner_id,
                activity_type=ActivityType.FOLLOW_UP,
                started_at=payload.next_action_at,
                next_action=payload.next_action,
            )
        )
    return activity


def list_activities(
    db: Session,
    actor: CurrentStaff,
    *,
    page: int,
    page_size: int,
    owner_id: UUID | None = None,
    activity_type: ActivityType | None = None,
    start_from: datetime | None = None,
    start_to: datetime | None = None,
) -> tuple[list[CrmActivity], int]:
    _ensure_sales_read(actor)
    query = select(CrmActivity)
    if not _can_read_all(actor):
        query = query.where(CrmActivity.owner_id == actor.staff.id)
    elif owner_id is not None:
        query = query.where(CrmActivity.owner_id == owner_id)
    if activity_type is not None:
        query = query.where(CrmActivity.activity_type == activity_type)
    if start_from is not None:
        query = query.where(CrmActivity.started_at >= start_from)
    if start_to is not None:
        query = query.where(CrmActivity.started_at < start_to)
    return _paginate(
        db, query.order_by(CrmActivity.started_at.desc()), page=page, page_size=page_size
    )


def update_activity(
    db: Session, actor: CurrentStaff, activity_id: UUID, payload: ActivityUpdate
) -> CrmActivity:
    _ensure_sales_write(actor)
    activity = db.get(CrmActivity, activity_id)
    if activity is None:
        raise _not_found("activity")
    _ensure_owner_access(actor, activity.owner_id, write=True)
    changes = payload.model_dump(exclude_unset=True, exclude={"create_follow_up"})
    for key, value in changes.items():
        setattr(activity, key, value)
    if payload.create_follow_up:
        if activity.completed_at is None or activity.next_action_at is None:
            raise ApiError(
                status_code=422,
                code="CRM_FOLLOW_UP_INVALID",
                message=FOLLOW_UP_INVALID_MESSAGE,
            )
        db.add(
            CrmActivity(
                account_id=activity.account_id,
                contact_id=activity.contact_id,
                opportunity_id=activity.opportunity_id,
                owner_id=activity.owner_id,
                activity_type=ActivityType.FOLLOW_UP,
                started_at=activity.next_action_at,
                next_action=activity.next_action,
            )
        )
    return activity


def my_day(db: Session, actor: CurrentStaff) -> MyDayResponse:
    _ensure_sales_read(actor)
    now = datetime.now(UTC)
    tomorrow = datetime.combine(date.today() + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    today = tomorrow - timedelta(days=1)
    owner = actor.staff.id
    follow_ups = list(
        db.scalars(
            select(CrmActivity)
            .where(
                CrmActivity.owner_id == owner,
                CrmActivity.completed_at.is_(None),
                CrmActivity.started_at >= today,
                CrmActivity.started_at < tomorrow,
            )
            .order_by(CrmActivity.started_at)
        )
    )
    overdue = list(
        db.scalars(
            select(CrmActivity)
            .where(
                CrmActivity.owner_id == owner,
                CrmActivity.completed_at.is_(None),
                CrmActivity.started_at < today,
            )
            .order_by(CrmActivity.started_at)
        )
    )
    meetings = list(
        db.scalars(
            select(CrmActivity)
            .where(
                CrmActivity.owner_id == owner,
                CrmActivity.activity_type == ActivityType.MEETING,
                CrmActivity.started_at >= today,
                CrmActivity.started_at < tomorrow + timedelta(days=7),
            )
            .order_by(CrmActivity.started_at)
        )
    )
    recent = list(
        db.scalars(
            select(CrmActivity)
            .where(
                CrmActivity.owner_id == owner,
                CrmActivity.completed_at.is_not(None),
                CrmActivity.completed_at <= now,
            )
            .order_by(CrmActivity.completed_at.desc())
            .limit(20)
        )
    )
    leads = list(
        db.scalars(
            select(CrmAccount)
            .where(
                CrmAccount.owner_id == owner,
                CrmAccount.status == AccountStatus.NEW,
                CrmAccount.archived_at.is_(None),
            )
            .order_by(CrmAccount.created_at.desc())
            .limit(20)
        )
    )
    return MyDayResponse(
        follow_ups_today=follow_ups,
        overdue=overdue,
        meetings=meetings,
        recent_activity=recent,
        new_leads=leads,
    )


def pipeline_summary(db: Session, actor: CurrentStaff) -> list[PipelineStageSummary]:
    _ensure_sales_read(actor)
    query = select(
        CrmOpportunity.stage,
        func.count(CrmOpportunity.id),
        func.coalesce(func.sum(CrmOpportunity.estimated_value_cents), 0),
        func.coalesce(func.sum(CrmOpportunity.weighted_value_cents), 0),
    ).where(CrmOpportunity.status == OpportunityStatus.OPEN)
    if not _can_read_all(actor):
        query = query.where(CrmOpportunity.owner_id == actor.staff.id)
    rows = db.execute(query.group_by(CrmOpportunity.stage)).all()
    by_stage = {row[0]: row for row in rows}
    return [
        PipelineStageSummary(
            stage=stage,
            deals=int(by_stage.get(stage, (stage, 0, 0, 0))[1]),
            value_cents=int(by_stage.get(stage, (stage, 0, 0, 0))[2]),
            weighted_value_cents=int(by_stage.get(stage, (stage, 0, 0, 0))[3]),
        )
        for stage in OpportunityStage
        if stage not in {OpportunityStage.WON, OpportunityStage.LOST, OpportunityStage.DISQUALIFIED}
    ]


def leaderboard(
    db: Session, actor: CurrentStaff, *, start: datetime, end: datetime
) -> list[LeaderboardRow]:
    _ensure_sales_read(actor)
    staff_query = select(StaffMember).where(StaffMember.active.is_(True))
    if not _can_read_all(actor):
        staff_query = staff_query.where(StaffMember.id == actor.staff.id)
    staff_members = list(db.scalars(staff_query.order_by(StaffMember.display_name)))
    result: list[LeaderboardRow] = []
    for member in staff_members:
        activities = list(
            db.scalars(
                select(CrmActivity).where(
                    CrmActivity.owner_id == member.id,
                    CrmActivity.started_at >= start,
                    CrmActivity.started_at < end,
                )
            )
        )
        opportunities = list(
            db.scalars(
                select(CrmOpportunity).where(
                    CrmOpportunity.owner_id == member.id,
                    CrmOpportunity.created_at >= start,
                    CrmOpportunity.created_at < end,
                )
            )
        )
        stage_counts = {
            stage: sum(item.stage == stage for item in opportunities) for stage in OpportunityStage
        }
        result.append(
            LeaderboardRow(
                owner_id=member.id,
                owner_name=member.display_name,
                contacts=len(activities),
                meetings=sum(item.activity_type == ActivityType.MEETING for item in activities),
                demos=sum(item.activity_type == ActivityType.DEMO for item in activities),
                proposals=sum(item.activity_type == ActivityType.PROPOSAL for item in activities),
                signed=stage_counts[OpportunityStage.PARTNER_SIGNED],
                activated=stage_counts[OpportunityStage.PARTNER_ACTIVATED],
                won=stage_counts[OpportunityStage.WON],
                revenue_cents=sum(
                    item.estimated_value_cents
                    for item in opportunities
                    if item.status == OpportunityStatus.WON
                ),
                pipeline_cents=sum(
                    item.estimated_value_cents
                    for item in opportunities
                    if item.status == OpportunityStatus.OPEN
                ),
                weighted_pipeline_cents=sum(
                    item.weighted_value_cents
                    for item in opportunities
                    if item.status == OpportunityStatus.OPEN
                ),
            )
        )
    return sorted(
        result, key=lambda row: (row.revenue_cents, row.weighted_pipeline_cents), reverse=True
    )
