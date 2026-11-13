from __future__ import annotations

import random
from datetime import timedelta

from sqlmodel import Session, select

from .collector import collect_round
from .models import Alert, Competitor, PricePoint, Product, User
from .models import utcnow
from .security import hash_password

DEMO_EMAIL = "demo@pricelens.it"
DEMO_PASSWORD = "demo1234"

COMPETITORS = [
    {"name": "Amazon", "domain": "amazon.it", "type": "marketplace", "base_ratio": 0.96, "volatility": 0.015, "promo_prob": 0.10, "stockout_prob": 0.01},
    {"name": "MediaWorld", "domain": "mediaworld.it", "type": "retailer", "base_ratio": 1.03, "volatility": 0.02, "promo_prob": 0.06, "stockout_prob": 0.02},
    {"name": "ePrice", "domain": "eprice.it", "type": "retailer", "base_ratio": 0.99, "volatility": 0.025, "promo_prob": 0.08, "stockout_prob": 0.02},
    {"name": "eBay", "domain": "ebay.it", "type": "marketplace", "base_ratio": 0.90, "volatility": 0.03, "promo_prob": 0.12, "stockout_prob": 0.03},
    {"name": "Unieuro", "domain": "unieuro.it", "type": "retailer", "base_ratio": 1.06, "volatility": 0.02, "promo_prob": 0.05, "stockout_prob": 0.02},
    {"name": "Zalando", "domain": "zalando.it", "type": "retailer", "base_ratio": 1.01, "volatility": 0.02, "promo_prob": 0.09, "stockout_prob": 0.02},
]

PRODUCTS = [
    {"sku": "APP-IP15-128", "name": "iPhone 15 128GB", "brand": "Apple", "category": "Smartphone", "cost": 650.0, "price": 799.0, "msrp": 899.0, "map": 799.0, "strategy": "margin_protected"},
    {"sku": "SAM-S24-256", "name": "Galaxy S24 256GB", "brand": "Samsung", "category": "Smartphone", "cost": 550.0, "price": 699.0, "msrp": 799.0, "map": 699.0, "strategy": "undercut"},
    {"sku": "SON-WH1000XM5", "name": "WH-1000XM5", "brand": "Sony", "category": "Audio", "cost": 250.0, "price": 379.0, "msrp": 399.0, "map": 349.0, "strategy": "match_min"},
    {"sku": "APP-AIRPODS-PRO2", "name": "AirPods Pro 2", "brand": "Apple", "category": "Audio", "cost": 180.0, "price": 249.0, "msrp": 279.0, "map": 229.0, "strategy": "premium"},
    {"sku": "LG-OLED55C3", "name": "OLED 55\" C3", "brand": "LG", "category": "TV", "cost": 900.0, "price": 1199.0, "msrp": 1399.0, "map": 1199.0, "strategy": "margin_protected"},
    {"sku": "DYS-V15", "name": "Dyson V15 Detect", "brand": "Dyson", "category": "Casa", "cost": 450.0, "price": 599.0, "msrp": 699.0, "map": 599.0, "strategy": "undercut"},
    {"sku": "NES-VERTUO-NEXT", "name": "Vertuo Next", "brand": "Nespresso", "category": "Casa", "cost": 80.0, "price": 129.0, "msrp": 149.0, "map": 119.0, "strategy": "match_min"},
    {"sku": "PHI-AIRFRYER-XXL", "name": "Airfryer XXL", "brand": "Philips", "category": "Casa", "cost": 150.0, "price": 219.0, "msrp": 249.0, "map": 199.0, "strategy": "margin_protected"},
    {"sku": "DYS-AIRWRAP", "name": "Dyson Airwrap", "brand": "Dyson", "category": "Bellezza", "cost": 400.0, "price": 549.0, "msrp": 599.0, "map": 549.0, "strategy": "premium"},
    {"sku": "LRP-SERUM", "name": "Siero Idratante 30ml", "brand": "La Roche-Posay", "category": "Bellezza", "cost": 15.0, "price": 29.9, "msrp": 35.0, "map": 24.9, "strategy": "match_min"},
    {"sku": "GAR-FR265", "name": "Forerunner 265", "brand": "Garmin", "category": "Sport", "cost": 320.0, "price": 429.0, "msrp": 449.0, "map": 399.0, "strategy": "margin_protected"},
    {"sku": "NIKE-PEGASUS40", "name": "Air Zoom Pegasus 40", "brand": "Nike", "category": "Sport", "cost": 70.0, "price": 119.0, "msrp": 139.0, "map": 109.0, "strategy": "undercut"},
]


def _simulate_series(base: float, volatility: float, promo_prob: float, n: int) -> list[float | None]:
    """Generate a mean-reverting price series of length n (None = stockout)."""
    prices: list[float | None] = []
    current = base
    for _ in range(n):
        if random.random() < 0.02:
            prices.append(None)
            continue
        if current is None:
            current = base * random.uniform(0.97, 1.03)
        elif random.random() < promo_prob:
            current = base * random.uniform(0.80, 0.94)
        else:
            current = current + (base - current) * 0.3 + base * random.uniform(-volatility, volatility)
            current = max(base * 0.7, current)
        prices.append(round(current, 2))
    return prices


def seed_demo(session: Session) -> dict:
    """Populate the database with a demo user, products, competitors and history (idempotent)."""
    existing = session.exec(select(User).limit(1)).first()
    if existing is not None:
        return {"seeded": False, "reason": "database already populated"}

    random.seed(42)

    demo_user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
    session.add(demo_user)
    session.commit()
    session.refresh(demo_user)

    competitors: list[Competitor] = []
    for item in COMPETITORS:
        cfg = {
            "base_ratio": item["base_ratio"],
            "volatility": item["volatility"],
            "promo_prob": item["promo_prob"],
            "stockout_prob": item["stockout_prob"],
        }
        competitor = Competitor(
            user_id=demo_user.id,
            name=item["name"],
            domain=item["domain"],
            type=item["type"],
            currency="EUR",
            price_source_type="simulated",
            price_source_config=cfg,
        )
        session.add(competitor)
        competitors.append(competitor)

    products: list[Product] = []
    for item in PRODUCTS:
        product = Product(
            user_id=demo_user.id,
            sku=item["sku"],
            name=item["name"],
            brand=item["brand"],
            category=item["category"],
            cost_price=item["cost"],
            current_price=item["price"],
            msrp=item["msrp"],
            map_price=item["map"],
            currency="EUR",
            strategy=item["strategy"],
            min_margin_pct=15.0,
        )
        session.add(product)
        products.append(product)

    session.commit()

    # 60 days of daily history per product x competitor
    now = utcnow()
    days = 60
    for product in products:
        for competitor in competitors:
            cfg = competitor.price_source_config or {}
            base = product.current_price * float(cfg.get("base_ratio", 1.0))
            series = _simulate_series(
                base,
                float(cfg.get("volatility", 0.02)),
                float(cfg.get("promo_prob", 0.06)),
                days,
            )
            for offset, price in enumerate(reversed(series)):
                stock = "in_stock" if price is not None else "out_of_stock"
                session.add(
                    PricePoint(
                        user_id=demo_user.id,
                        product_id=product.id,
                        competitor_id=competitor.id,
                        price=price,
                        currency="EUR",
                        stock_status=stock,
                        captured_at=now - timedelta(days=offset + 1, hours=3),
                    )
                )

    session.commit()

    # One fresh round to add "today" observations and realistic alerts
    collect_round(session, user_id=demo_user.id)

    # Mark some alerts as already read for a realistic mix
    alerts = session.exec(select(Alert)).all()
    for i, alert in enumerate(alerts):
        if i % 3 == 0:
            alert.read = True
    session.commit()

    return {
        "seeded": True,
        "products": len(products),
        "competitors": len(competitors),
        "demo_email": DEMO_EMAIL,
        "demo_password": DEMO_PASSWORD,
    }
