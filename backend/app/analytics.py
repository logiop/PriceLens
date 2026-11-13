from __future__ import annotations

from sqlmodel import Session, select

from .models import Competitor, PricePoint, Product
from .schemas import RepricingRecommendation


def _in_stock(pp: PricePoint) -> bool:
    return pp.stock_status == "in_stock" and pp.price is not None


def latest_prices(session: Session, product_id: int) -> dict[int, tuple[PricePoint, PricePoint | None]]:
    """Return {competitor_id: (latest, previous)} price points for a product."""
    points = session.exec(
        select(PricePoint)
        .where(PricePoint.product_id == product_id)
        .order_by(PricePoint.competitor_id, PricePoint.captured_at.desc())
    ).all()

    result: dict[int, tuple[PricePoint, PricePoint | None]] = {}
    for pp in points:
        if pp.competitor_id not in result:
            result[pp.competitor_id] = (pp, None)
        elif result[pp.competitor_id][1] is None:
            result[pp.competitor_id] = (result[pp.competitor_id][0], pp)
    return result


def market_stats(session: Session, product: Product) -> dict:
    """Compute min/max/avg competitor price, position and price index."""
    latest = latest_prices(session, product.id)
    prices = [latest_pp.price for (latest_pp, _prev) in latest.values() if _in_stock(latest_pp)]
    if not prices:
        return {
            "min_price": None,
            "max_price": None,
            "avg_price": None,
            "position": None,
            "price_index": None,
            "last_change_pct": None,
            "competitors_tracked": len(latest),
        }

    position = None
    if product.current_price is not None:
        ordered = sorted(set(prices))
        position = sum(1 for p in ordered if p < product.current_price) + 1
        position = min(position, len(prices) + 1)

    price_index = None
    if position is not None and prices:
        # cheaper than everyone -> 100; most expensive -> ~0
        price_index = round(100 * (len(prices) - position + 1) / len(prices), 1)

    avg_price = round(sum(prices) / len(prices), 2)

    # last change: average % change across competitors' latest vs previous
    changes = []
    for latest_pp, prev in latest.values():
        if prev is not None and prev.price and latest_pp.price:
            changes.append((latest_pp.price - prev.price) / prev.price * 100)
    last_change_pct = round(sum(changes) / len(changes), 2) if changes else None

    return {
        "min_price": round(min(prices), 2),
        "max_price": round(max(prices), 2),
        "avg_price": avg_price,
        "position": position,
        "price_index": price_index,
        "last_change_pct": last_change_pct,
        "competitors_tracked": len(latest),
    }


def repricing_recommendation(session: Session, product: Product) -> RepricingRecommendation:
    """Suggest an optimal price using the product's chosen strategy."""
    latest = latest_prices(session, product.id)
    prices = [pp.price for (pp, _prev) in latest.values() if _in_stock(pp)]

    floor = max(product.map_price or 0.0, product.cost_price * (1 + product.min_margin_pct / 100))
    floor = round(floor, 2)

    min_c = min(prices) if prices else None
    max_c = max(prices) if prices else None
    ceiling = product.msrp or (round(max_c * 1.05, 2) if max_c else None)

    if min_c is None:
        target = product.msrp or product.cost_price * (1 + product.min_margin_pct / 100)
        rationale = "Nessun prezzo competitor disponibile: applico un prezzo che protegge il margine."
    elif product.strategy == "match_min":
        target = min_c - max(0.01, min_c * 0.01)
        rationale = "Strategia 'allinea al minimo': prezzo appena sotto il competitor più economico."
    elif product.strategy == "undercut":
        target = min_c * 0.98
        rationale = "Strategia 'sottoquotazione': prezzo del 2% sotto il competitor più economico."
    elif product.strategy == "premium":
        target = ceiling or (max_c * 1.03 if max_c else product.current_price)
        rationale = "Strategia 'premium': posizionamento al top della fascia di prezzo."
    else:  # margin_protected
        target = max(floor, min_c)
        rationale = "Strategia 'margine protetto': allineo al minimo competitor senza scendere sotto il margine."

    target = round(max(floor, target), 2)
    if ceiling is not None:
        target = round(min(target, ceiling), 2)

    margin_pct = round((target - product.cost_price) / target * 100, 2) if target else 0.0
    delta_pct = round((target - product.current_price) / product.current_price * 100, 2) if product.current_price else 0.0

    new_position = None
    if target is not None and prices:
        ordered = sorted(set(prices))
        new_position = min(sum(1 for p in ordered if p < target) + 1, len(prices) + 1)

    return RepricingRecommendation(
        product_id=product.id,
        sku=product.sku,
        name=product.name,
        current_price=product.current_price,
        suggested_price=target,
        margin_pct=margin_pct,
        delta_pct=delta_pct,
        rationale=rationale,
        new_position=new_position,
        floor=floor,
        ceiling=ceiling,
    )


def competitor_name(session: Session, competitor_id: int | None) -> str | None:
    if competitor_id is None:
        return None
    comp = session.get(Competitor, competitor_id)
    return comp.name if comp else None
