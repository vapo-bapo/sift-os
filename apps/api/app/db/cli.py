import argparse

from app.db.session import SessionLocal
from app.staff.seed import seed_staff


def main() -> None:
    parser = argparse.ArgumentParser(description="SIFT OS database utilities")
    parser.add_argument("command", choices=("seed-staff",))
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.command == "seed-staff":
            seed_staff(db)
            db.commit()


if __name__ == "__main__":
    main()
