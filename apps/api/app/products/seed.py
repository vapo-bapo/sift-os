from dataclasses import dataclass

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.products.models import Product


@dataclass(frozen=True, slots=True)
class ProductSeed:
    code: str
    name: str


PRODUCT_SEEDS = (
    ProductSeed("ARGUS", "ARGUS"),
    ProductSeed("LYNX", "LYNX"),
    ProductSeed("COLLAB", "Collab"),
)


def seed_products(db: Session) -> None:
    for product in PRODUCT_SEEDS:
        db.execute(
            insert(Product)
            .values(code=product.code, name=product.name, active=True)
            .on_conflict_do_update(
                index_elements=[Product.code],
                set_={"name": product.name, "active": True},
            )
        )
