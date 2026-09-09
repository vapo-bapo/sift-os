from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.crm.models import AccountStatus, AccountType, ActivityType, OpportunityStage
from app.crm.schemas import (
    AccountCreate,
    AccountCsvImportRequest,
    AccountCsvImportResponse,
    AccountCsvRequest,
    AccountResponse,
    AccountUpdate,
    ActivityCreate,
    ActivityResponse,
    ActivityUpdate,
    AssignmentRequest,
    CaseStudyMetricsResponse,
    CaseStudyMetricsUpdate,
    ContactCreate,
    ContactResponse,
    ContactUpdate,
    CsvParseResult,
    LeaderboardRow,
    MyDayResponse,
    OpportunityCreate,
    OpportunityResponse,
    OpportunityUpdate,
    Page,
    PipelineStageSummary,
    StageChangeRequest,
)
from app.crm.service import (
    archive_account,
    assign_opportunity,
    change_opportunity_stage,
    create_account,
    create_activity,
    create_contact,
    create_opportunity,
    get_account,
    get_case_study_metrics,
    import_accounts,
    leaderboard,
    list_accounts,
    list_activities,
    list_contacts,
    list_opportunities,
    my_day,
    pipeline_summary,
    preview_account_import,
    seed_case_studies,
    update_account,
    update_activity,
    update_contact,
    update_opportunity,
    upsert_case_study_metrics,
)
from app.db.session import get_db
from app.staff.dependencies import CurrentStaff, get_current_staff, require_csrf

router = APIRouter(prefix="/api", tags=["crm"])

Db = Annotated[Session, Depends(get_db)]
Staff = Annotated[CurrentStaff, Depends(get_current_staff)]
CsrfStaff = Annotated[CurrentStaff, Depends(require_csrf)]
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


@router.get("/accounts", response_model=Page[AccountResponse])
def accounts(
    db: Db,
    current: Staff,
    page: PageNumber = 1,
    page_size: PageSize = 25,
    search: str | None = None,
    owner_id: UUID | None = None,
    account_type: AccountType | None = None,
    status: AccountStatus | None = None,
) -> Page[AccountResponse]:
    items, total = list_accounts(
        db,
        current,
        page=page,
        page_size=page_size,
        search=search,
        owner_id=owner_id,
        account_type=account_type,
        status=status,
    )
    return Page(
        items=[AccountResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/accounts", response_model=AccountResponse, status_code=201)
def add_account(payload: AccountCreate, db: Db, current: Staff, csrf: CsrfStaff) -> AccountResponse:
    del csrf
    account = create_account(db, current, payload)
    db.commit()
    db.refresh(account)
    return AccountResponse.model_validate(account)


@router.post("/accounts/import/preview", response_model=CsvParseResult)
def preview_accounts_import(payload: AccountCsvRequest, db: Db, current: Staff) -> CsvParseResult:
    return preview_account_import(db, current, payload.csv_content)


@router.post("/accounts/import", response_model=AccountCsvImportResponse, status_code=201)
def execute_accounts_import(
    payload: AccountCsvImportRequest,
    db: Db,
    current: Staff,
    csrf: CsrfStaff,
) -> AccountCsvImportResponse:
    del csrf
    result = import_accounts(db, current, payload.csv_content, confirmed=payload.confirm)
    db.commit()
    return result


@router.post("/case-studies/seed", response_model=list[AccountResponse])
def initialize_case_studies(db: Db, current: Staff, csrf: CsrfStaff) -> list[AccountResponse]:
    del csrf
    accounts = seed_case_studies(db, current)
    db.commit()
    return [AccountResponse.model_validate(account) for account in accounts]


@router.get("/case-studies/{account_id}/metrics", response_model=CaseStudyMetricsResponse)
def case_study_metrics(account_id: UUID, db: Db, current: Staff) -> CaseStudyMetricsResponse:
    return CaseStudyMetricsResponse.model_validate(get_case_study_metrics(db, current, account_id))


@router.put("/case-studies/{account_id}/metrics", response_model=CaseStudyMetricsResponse)
def save_case_study_metrics(
    account_id: UUID,
    payload: CaseStudyMetricsUpdate,
    db: Db,
    current: Staff,
    csrf: CsrfStaff,
) -> CaseStudyMetricsResponse:
    del csrf
    metrics = upsert_case_study_metrics(db, current, account_id, payload)
    db.commit()
    db.refresh(metrics)
    return CaseStudyMetricsResponse.model_validate(metrics)


@router.get("/accounts/{account_id}", response_model=AccountResponse)
def account_detail(account_id: UUID, db: Db, current: Staff) -> AccountResponse:
    return AccountResponse.model_validate(get_account(db, current, account_id))


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
def edit_account(
    account_id: UUID, payload: AccountUpdate, db: Db, current: Staff, csrf: CsrfStaff
) -> AccountResponse:
    del csrf
    account = update_account(db, current, account_id, payload)
    db.commit()
    db.refresh(account)
    return AccountResponse.model_validate(account)


@router.post("/accounts/{account_id}/archive", response_model=AccountResponse)
def remove_account(account_id: UUID, db: Db, current: Staff, csrf: CsrfStaff) -> AccountResponse:
    del csrf
    account = archive_account(db, current, account_id)
    db.commit()
    db.refresh(account)
    return AccountResponse.model_validate(account)


@router.get("/contacts", response_model=Page[ContactResponse])
def contacts(
    db: Db,
    current: Staff,
    page: PageNumber = 1,
    page_size: PageSize = 25,
    account_id: UUID | None = None,
    search: str | None = None,
) -> Page[ContactResponse]:
    items, total = list_contacts(
        db, current, page=page, page_size=page_size, account_id=account_id, search=search
    )
    return Page(
        items=[ContactResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/contacts", response_model=ContactResponse, status_code=201)
def add_contact(payload: ContactCreate, db: Db, current: Staff, csrf: CsrfStaff) -> ContactResponse:
    del csrf
    contact = create_contact(db, current, payload)
    db.commit()
    db.refresh(contact)
    return ContactResponse.model_validate(contact)


@router.patch("/contacts/{contact_id}", response_model=ContactResponse)
def edit_contact(
    contact_id: UUID, payload: ContactUpdate, db: Db, current: Staff, csrf: CsrfStaff
) -> ContactResponse:
    del csrf
    contact = update_contact(db, current, contact_id, payload)
    db.commit()
    db.refresh(contact)
    return ContactResponse.model_validate(contact)


@router.get("/opportunities", response_model=Page[OpportunityResponse])
def opportunities(
    db: Db,
    current: Staff,
    page: PageNumber = 1,
    page_size: PageSize = 25,
    owner_id: UUID | None = None,
    stage: OpportunityStage | None = None,
    search: str | None = None,
    stale_days: Annotated[int | None, Query(ge=1, le=365)] = None,
) -> Page[OpportunityResponse]:
    items, total = list_opportunities(
        db,
        current,
        page=page,
        page_size=page_size,
        owner_id=owner_id,
        stage=stage,
        search=search,
        stale_days=stale_days,
    )
    return Page(
        items=[OpportunityResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/opportunities", response_model=OpportunityResponse, status_code=201)
def add_opportunity(
    payload: OpportunityCreate, db: Db, current: Staff, csrf: CsrfStaff
) -> OpportunityResponse:
    del csrf
    opportunity = create_opportunity(db, current, payload)
    db.commit()
    db.refresh(opportunity)
    return OpportunityResponse.model_validate(opportunity)


@router.patch("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
def edit_opportunity(
    opportunity_id: UUID,
    payload: OpportunityUpdate,
    db: Db,
    current: Staff,
    csrf: CsrfStaff,
) -> OpportunityResponse:
    del csrf
    opportunity = update_opportunity(db, current, opportunity_id, payload)
    db.commit()
    db.refresh(opportunity)
    return OpportunityResponse.model_validate(opportunity)


@router.post("/opportunities/{opportunity_id}/stage", response_model=OpportunityResponse)
def move_opportunity(
    opportunity_id: UUID,
    payload: StageChangeRequest,
    db: Db,
    current: Staff,
    csrf: CsrfStaff,
) -> OpportunityResponse:
    del csrf
    opportunity = change_opportunity_stage(
        db, current, opportunity_id, payload.stage, payload.lost_reason
    )
    db.commit()
    db.refresh(opportunity)
    return OpportunityResponse.model_validate(opportunity)


@router.post("/opportunities/{opportunity_id}/assign", response_model=OpportunityResponse)
def reassign_opportunity(
    opportunity_id: UUID,
    payload: AssignmentRequest,
    db: Db,
    current: Staff,
    csrf: CsrfStaff,
) -> OpportunityResponse:
    del csrf
    opportunity = assign_opportunity(db, current, opportunity_id, payload.owner_id)
    db.commit()
    db.refresh(opportunity)
    return OpportunityResponse.model_validate(opportunity)


@router.get("/activities", response_model=Page[ActivityResponse])
def activities(
    db: Db,
    current: Staff,
    page: PageNumber = 1,
    page_size: PageSize = 25,
    owner_id: UUID | None = None,
    activity_type: ActivityType | None = None,
    start_from: datetime | None = None,
    start_to: datetime | None = None,
) -> Page[ActivityResponse]:
    items, total = list_activities(
        db,
        current,
        page=page,
        page_size=page_size,
        owner_id=owner_id,
        activity_type=activity_type,
        start_from=start_from,
        start_to=start_to,
    )
    return Page(
        items=[ActivityResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/activities", response_model=ActivityResponse, status_code=201)
def add_activity(
    payload: ActivityCreate, db: Db, current: Staff, csrf: CsrfStaff
) -> ActivityResponse:
    del csrf
    activity = create_activity(db, current, payload)
    db.commit()
    db.refresh(activity)
    return ActivityResponse.model_validate(activity)


@router.patch("/activities/{activity_id}", response_model=ActivityResponse)
def edit_activity(
    activity_id: UUID, payload: ActivityUpdate, db: Db, current: Staff, csrf: CsrfStaff
) -> ActivityResponse:
    del csrf
    activity = update_activity(db, current, activity_id, payload)
    db.commit()
    db.refresh(activity)
    return ActivityResponse.model_validate(activity)


@router.get("/sales/my-day", response_model=MyDayResponse)
def sales_my_day(db: Db, current: Staff) -> MyDayResponse:
    return my_day(db, current)


@router.get("/sales/pipeline", response_model=list[PipelineStageSummary])
def sales_pipeline(db: Db, current: Staff) -> list[PipelineStageSummary]:
    return pipeline_summary(db, current)


@router.get("/sales/leaderboard", response_model=list[LeaderboardRow])
def sales_leaderboard(
    db: Db,
    current: Staff,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[LeaderboardRow]:
    range_end = end or datetime.now(UTC)
    range_start = start or range_end - timedelta(days=30)
    return leaderboard(db, current, start=range_start, end=range_end)
