from __future__ import annotations

from fastapi import APIRouter, Query
from sqlmodel import select

from ..analytics import market_stats
from ..database import SessionDep
from ..models import Alert, Competitor, PricePoint, Product
from ..models import utcnow
from ..routers.alerts import _to_read
from ..security import CurrentTeamDep

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(
    team: CurrentTeamDep,
    session: SessionDep,
    recent_alerts: int = Query(default=6, ge=1, le=50),
):
    products = session.exec(
        select(Product).where(Product.team_id == team.id, Product.active.is_(True))
    ).all()
    competitors = session.exec(
        select(Competitor).where(Competitor.team_id == team.id, Competitor.active.is_(True))
    ).all()
    alerts = session.exec(select(Alert).where(Alert.team_id == team.id)).all()

    open_alerts = [a for a in alerts if not a.read]
    critical = [a for a in open_alerts if a.severity == "critical"]

    today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    points_today = len(
        session.exec(
            select(PricePoint).where(
                PricePoint.team_id == team.id, PricePoint.captured_at >= today_start
            )
        ).all()
    )

    stats = {p.id: market_stats(session, p) for p in products}
    indices = [s["price_index"] for s in stats.values() if s["price_index"] is not None]
    avg_index = round(sum(indices) / len(indices), 1) if indices else None

    movers = [
        {
            "product_id": p.id,
            "sku": p.sku,
            "name": p.name,
            "brand": p.brand,
            "category": p.category,
            "current_price": p.current_price,
            "change_pct": stats[p.id]["last_change_pct"],
            "position": stats[p.id]["position"],
            "price_index": stats[p.id]["price_index"],
        }
        for p in products
        if stats[p.id]["last_change_pct"] is not None
    ]
    movers.sort(key=lambda m: abs(m["change_pct"]), reverse=True)

    distribution = [
        {"product_id": p.id, "name": p.name, "sku": p.sku, "price_index": stats[p.id]["price_index"]}
        for p in products
    ]

    recent = session.exec(
        select(Alert).where(Alert.team_id == team.id).order_by(Alert.created_at.desc()).limit(recent_alerts)
    ).all()

    return {
        "kpis": {
            "products": len(products),
            "competitors": len(competitors),
            "open_alerts": len(open_alerts),
            "critical_alerts": len(critical),
            "points_today": points_today,
            "avg_price_index": avg_index,
        },
        "top_movers": movers[:6],
        "price_index_distribution": distribution,
        "recent_alerts": [_to_read(session, a) for a in recent],
    }
