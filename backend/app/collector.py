from __future__ import annotations

import json
import random
import re

import httpx
from bs4 import BeautifulSoup
from sqlmodel import Session, select

from .models import Alert, Competitor, PricePoint, Product
from .schemas import CollectResult

PRICE_DROP_THRESHOLD_PCT = 3.0
PRICE_RISE_THRESHOLD_PCT = 3.0


def _last_point(session: Session, product_id: int, competitor_id: int) -> PricePoint | None:
    return session.exec(
        select(PricePoint)
        .where(PricePoint.product_id == product_id, PricePoint.competitor_id == competitor_id)
        .order_by(PricePoint.captured_at.desc())
    ).first()


def _simulate(competitor: Competitor, product: Product, last: PricePoint | None) -> tuple[float | None, str]:
    """Generate the next simulated price for a competitor/product pair."""
    cfg = competitor.price_source_config or {}
    base_ratio = float(cfg.get("base_ratio", 1.0))
    volatility = float(cfg.get("volatility", 0.02))
    promo_prob = float(cfg.get("promo_prob", 0.06))
    stockout_prob = float(cfg.get("stockout_prob", 0.02))

    base = product.current_price * base_ratio

    if last is not None and last.stock_status == "out_of_stock":
        if random.random() < 0.7:
            price = round(base * random.uniform(0.97, 1.03), 2)
            return price, "in_stock"
        return None, "out_of_stock"

    if random.random() < stockout_prob:
        return None, "out_of_stock"

    if last is None or last.price is None:
        price = round(base * random.uniform(0.97, 1.03), 2)
    elif random.random() < promo_prob:
        price = round(base * random.uniform(0.80, 0.94), 2)
    else:
        # mean-reverting random walk around the competitor's base price
        price = last.price + (base - last.price) * 0.3 + base * random.uniform(-volatility, volatility)
        price = round(max(base * 0.7, price), 2)

    return price, "in_stock"


def _parse_amount(raw: str | None) -> float | None:
    """Parse a price string like '1.234,56', '99.99' or '1 234,56' into a float."""
    if not raw:
        return None
    cleaned = raw.strip().replace("\u00a0", " ").replace(" ", "")
    cleaned = re.sub(r"[^\d.,-]", "", cleaned)
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        # the rightmost separator is the decimal one
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def _walk_jsonld(obj) -> float | None:
    """Recursively find the first numeric `price` field in a JSON-LD structure."""
    if isinstance(obj, dict):
        if "price" in obj and isinstance(obj["price"], (int, float, str)):
            price = _parse_amount(str(obj["price"]))
            if price is not None:
                return price
        for value in obj.values():
            price = _walk_jsonld(value)
            if price is not None:
                return price
    elif isinstance(obj, list):
        for value in obj:
            price = _walk_jsonld(value)
            if price is not None:
                return price
    return None


def _extract_jsonld_price(html: str) -> float | None:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for obj in data if isinstance(data, list) else [data]:
            price = _walk_jsonld(obj)
            if price is not None:
                return price
    return None


def _extract_css_price(html: str, selector: str, attribute: str) -> float | None:
    soup = BeautifulSoup(html, "html.parser")
    element = soup.select_one(selector)
    if element is None:
        return None
    raw = element.get(attribute) if attribute and attribute != "text" else element.get_text()
    return _parse_amount(raw)


def _extract_regex_price(html: str, pattern: str) -> float | None:
    match = re.search(pattern, html)
    if match is None:
        return None
    if "price" in match.groupdict():
        raw = match.group("price")
    elif match.groups():
        raw = match.group(1)
    else:
        raw = match.group(0)
    return _parse_amount(raw)


def _fetch_url_price(competitor: Competitor) -> tuple[float | None, str] | None:
    """Attempt to scrape a price from a competitor product URL (best effort).

    Supports `selector_type`: jsonld (default, with a currency-pattern fallback),
    css (needs `selector` + optional `attribute`), regex (needs `pattern`).
    """
    cfg = competitor.price_source_config or {}
    url = cfg.get("url")
    if not url:
        return None
    timeout = float(cfg.get("timeout", 10.0))
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PriceLens/1.0; +pricing-intelligence)",
        "Accept": "text/html,application/xhtml+xml",
    }
    headers.update(cfg.get("headers") or {})
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=timeout, headers=headers)
        resp.raise_for_status()
        html = resp.text
    except Exception:
        return None

    selector_type = cfg.get("selector_type", "jsonld")
    price: float | None = None
    if selector_type == "css":
        price = _extract_css_price(
            html, cfg.get("selector", "meta[itemprop=price]"), cfg.get("attribute", "content")
        )
    elif selector_type == "regex":
        price = _extract_regex_price(html, cfg.get("pattern", r'[€$£]\s*([0-9][0-9.,]*)'))
    else:
        price = _extract_jsonld_price(html)
        if price is None:
            price = _extract_regex_price(
                html, r'[€$£]\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)'
            )

    if price is None:
        return None
    return price, "in_stock"


def _add_alert(
    session: Session,
    product: Product,
    competitor: Competitor,
    type_: str,
    severity: str,
    message: str,
) -> None:
    session.add(
        Alert(
            user_id=product.user_id,
            product_id=product.id,
            competitor_id=competitor.id,
            type=type_,
            severity=severity,
            message=message,
        )
    )


def _detect_alerts(
    session: Session,
    product: Product,
    competitor: Competitor,
    prev: PricePoint | None,
    new_price: float | None,
    new_stock: str,
) -> int:
    """Compare new observation vs previous and create alerts. Returns count created."""
    created = 0

    if prev is None:
        return created

    # Stock transitions
    if prev.stock_status == "in_stock" and new_stock == "out_of_stock":
        _add_alert(
            session,
            product,
            competitor,
            "out_of_stock",
            "warning",
            f"{competitor.name} ha esaurito lo stock di '{product.name}'.",
        )
        created += 1
    elif prev.stock_status == "out_of_stock" and new_stock == "in_stock":
        _add_alert(
            session,
            product,
            competitor,
            "back_in_stock",
            "info",
            f"{competitor.name} ha di nuovo disponibile '{product.name}'.",
        )
        created += 1

    # Price movement
    if prev.price and new_price:
        change_pct = (new_price - prev.price) / prev.price * 100
        if change_pct <= -PRICE_DROP_THRESHOLD_PCT:
            _add_alert(
                session,
                product,
                competitor,
                "price_drop",
                "warning",
                f"{competitor.name} ha abbassato '{product.name}' del {abs(change_pct):.1f}% "
                f"(da {prev.price:.2f} a {new_price:.2f} {product.currency}).",
            )
            created += 1
        elif change_pct >= PRICE_RISE_THRESHOLD_PCT:
            _add_alert(
                session,
                product,
                competitor,
                "price_rise",
                "info",
                f"{competitor.name} ha alzato '{product.name}' del {change_pct:.1f}% "
                f"(da {prev.price:.2f} a {new_price:.2f} {product.currency}).",
            )
            created += 1

    # MAP violation
    if new_price is not None and product.map_price is not None and new_price < product.map_price:
        _add_alert(
            session,
            product,
            competitor,
            "map_violation",
            "critical",
            f"{competitor.name} vende '{product.name}' sotto MAP "
            f"({new_price:.2f} < {product.map_price:.2f} {product.currency}).",
        )
        created += 1

    return created


def collect_round(session: Session, user_id: int | None = None) -> CollectResult:
    """Run one collection round across active products and competitors.

    When `user_id` is given, only that user's products and competitors are collected.
    """
    product_query = select(Product).where(Product.active.is_(True))
    competitor_query = select(Competitor).where(Competitor.active.is_(True))
    if user_id is not None:
        product_query = product_query.where(Product.user_id == user_id)
        competitor_query = competitor_query.where(Competitor.user_id == user_id)
    products = session.exec(product_query).all()
    competitors = session.exec(competitor_query).all()

    collected = 0
    alerts_created = 0
    skipped = 0
    errors = 0

    for product in products:
        for competitor in competitors:
            prev = _last_point(session, product.id, competitor.id)

            new_price: float | None
            new_stock: str
            if competitor.price_source_type == "url":
                result = _fetch_url_price(competitor)
                if result is None:
                    errors += 1
                    continue
                new_price, new_stock = result
            else:
                new_price, new_stock = _simulate(competitor, product, prev)

            session.add(
                PricePoint(
                    user_id=product.user_id,
                    product_id=product.id,
                    competitor_id=competitor.id,
                    price=new_price,
                    currency=competitor.currency,
                    stock_status=new_stock,
                    url=(competitor.price_source_config or {}).get("url"),
                )
            )
            collected += 1
            alerts_created += _detect_alerts(
                session, product, competitor, prev, new_price, new_stock
            )

    session.commit()
    return CollectResult(
        collected=collected,
        alerts_created=alerts_created,
        skipped=skipped,
        errors=errors,
    )
