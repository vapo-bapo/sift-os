import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crm.models import AccountStatus, AccountType, CrmAccount
from app.db.session import SessionLocal
from app.products.seed import seed_products
from app.staff.models import StaffMember
from app.staff.seed import seed_staff


def seed_case_studies(db: Session) -> None:
    owner = db.scalar(select(StaffMember).where(StaffMember.display_name == "Alessandro Bellucco"))
    if owner is None:
        return
    for name in ("Stral", "Auris"):
        exists = db.scalar(
            select(CrmAccount).where(
                CrmAccount.name == name, CrmAccount.account_type == AccountType.CASE_STUDY
            )
        )
        if exists is None:
            db.add(
                CrmAccount(
                    name=name,
                    account_type=AccountType.CASE_STUDY,
                    owner_id=owner.id,
                    status=AccountStatus.NEW,
                    lead_score=0,
                )
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="SIFT OS database utilities")
    parser.add_argument(
        "command", choices=("seed-staff", "seed-products", "seed-case-studies", "seed-all")
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.command in {"seed-staff", "seed-all"}:
            seed_staff(db)
        if args.command in {"seed-products", "seed-all"}:
            seed_products(db)
        if args.command in {"seed-case-studies", "seed-all"}:
            seed_case_studies(db)
        db.commit()


if __name__ == "__main__":
    main()
