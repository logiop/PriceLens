from __future__ import annotations

import csv
import io
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from openpyxl import Workbook
from sqlmodel import select

from ..analytics import market_stats
from ..database import SessionDep
from ..models import Alert, Competitor, PricePoint, Product
from ..models import utcnow
from ..security import CurrentUserDep

router = APIRouter(prefix="/export", tags=["export"])


def _dispatch(headers: list[str], rows: list[list], format: str, filename: str) -> Response:
    if format == "xlsx":
        return _xlsx(headers, rows, filename)
    return _csv(headers, rows, filename)


def _csv(headers: list[str], rows: list[list], filename: str) -> Response:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )


def _xlsx(headers: list[str], rows: list[list], filename: str) -> Response:
    wb = Workbook()
    ws = wb.active
    ws.title = "Export"
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}.xlsx"'},
    )


@router.get("/products")
def export_products(
    user: CurrentUserDep,
    session: SessionDep,
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
):
    products = session.exec(
        select(Product).where(Product.user_id == user.id).order_by(Product.name)
    ).all()
    headers = [
        "sku", "nome", "brand", "categoria", "ean", "costo", "prezzo", "msrp", "map",
        "strategia", "margine_min_%", "min_competitor", "max_competitor", "media_competitor",
        "posizione", "indice_competitivita",
    ]
    rows: list[list] = []
    for p in products:
        stats = market_stats(session, p)
        rows.append([
            p.sku, p.name, p.brand, p.category, p.ean or "", p.cost_price, p.current_price,
            p.msrp or "", p.map_price or "", p.strategy, p.min_margin_pct,
            stats["min_price"] if stats["min_price"] is not None else "",
            stats["max_price"] if stats["max_price"] is not None else "",
            stats["avg_price"] if stats["avg_price"] is not None else "",
            stats["position"] if stats["position"] is not None else "",
            stats["price_index"] if stats["price_index"] is not None else "",
        ])
    return _dispatch(headers, rows, format, "pricelens-prodotti")


@router.get("/alerts")
def export_alerts(
    user: CurrentUserDep,
    session: SessionDep,
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
):
    alerts = session.exec(
        select(Alert).where(Alert.user_id == user.id).order_by(Alert.created_at.desc())
    ).all()
    products = {p.id: p for p in session.exec(select(Product).where(Product.user_id == user.id)).all()}
    competitors = {c.id: c for c in session.exec(select(Competitor).where(Competitor.user_id == user.id)).all()}

    headers = ["data", "tipo", "severita", "letto", "prodotto", "competitor", "messaggio"]
    rows: list[list] = []
    for a in alerts:
        product = products.get(a.product_id)
        competitor = competitors.get(a.competitor_id) if a.competitor_id else None
        rows.append([
            a.created_at.isoformat(),
            a.type,
            a.severity,
            "si" if a.read else "no",
            product.name if product else "",
            competitor.name if competitor else "",
            a.message,
        ])
    return _dispatch(headers, rows, format, "pricelens-alert")


@router.get("/history/{product_id}")
def export_history(
    product_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    format: str = Query(default="csv", pattern="^(csv|xlsx)$"),
    days: int = Query(default=60, ge=1, le=365),
):
    product = session.get(Product, product_id)
    if product is None or product.user_id != user.id:
        raise HTTPException(status_code=404, detail="Prodotto non trovato")

    cutoff = utcnow() - timedelta(days=days)
    points = session.exec(
        select(PricePoint)
        .where(
            PricePoint.product_id == product_id,
            PricePoint.captured_at >= cutoff,
        )
        .order_by(PricePoint.captured_at)
    ).all()
    competitors = {
        c.id: c for c in session.exec(select(Competitor).where(Competitor.user_id == user.id)).all()
    }

    headers = ["data", "competitor", "prezzo", "disponibilita"]
    rows: list[list] = []
    for pp in points:
        comp = competitors.get(pp.competitor_id)
        rows.append([
            pp.captured_at.isoformat(),
            comp.name if comp else "",
            pp.price if pp.price is not None else "",
            pp.stock_status,
        ])
    return _dispatch(headers, rows, format, f"pricelens-storico-{product.sku}")
