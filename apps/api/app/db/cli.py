import argparse

from app.db.session import SessionLocal
from app.products.seed import seed_products
from app.staff.seed import seed_staff


def main() -> None:
    parser = argparse.ArgumentParser(description="SIFT OS database utilities")
    parser.add_argument("command", choices=("seed-staff", "seed-products", "seed-all"))
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.command in {"seed-staff", "seed-all"}:
            seed_staff(db)
        if args.command in {"seed-products", "seed-all"}:
            seed_products(db)
        db.commit()


if __name__ == "__main__":
    main()
