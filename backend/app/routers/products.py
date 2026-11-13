from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Query, Request
from sqlmodel import select

from ..analytics import latest_prices, market_stats, repricing_recommendation
from ..audit import log
from ..database import SessionDep
from ..models import Alert, Competitor, PricePoint, Product
from ..models import utcnow
from ..schemas import (
    CompetitorPrice,
    HistoryPoint,
    HistorySeries,
    ProductCreate,
    ProductDetail,
    ProductRead,
    ProductUpdate,
    RepricingRecommendation,
)
from ..security import CurrentTeamDep, CurrentUserDep

router = APIRouter(prefix="/products", tags=["products"])


def _get_owned(session: SessionDep, team_id: int, product_id: int) -> Product:
    product = session.get(Product, product_id)
    if product is None or product.team_id != team_id:
        raise HTTPException(status_code=404, detail="Prodotto non trovato")
    return product


def _open_alerts(session: SessionDep, product_id: int) -> int:
    return len(
        session.exec(select(Alert).where(Alert.product_id == product_id, Alert.read.is_(False))).all()
    )


def _to_read(
    session: SessionDep,
    product: Product,
    include_recommendation: bool = False,
) -> ProductRead:
    stats = market_stats(session, product)
    data = product.model_dump()
    data.update(stats)
    data["open_alerts"] = _open_alerts(session, product.id)
    if include_recommendation:
        data["recommendation"] = repricing_recommendation(session, product)
    return ProductRead(**data)


def _competitor_prices(session: SessionDep, product_id: int) -> list[CompetitorPrice]:
    latest = latest_prices(session, product_id)
    result: list[CompetitorPrice] = []
    competitor_ids = list(latest.keys())
    competitors = {
        c.id: c for c in session.exec(select(Competitor).where(Competitor.id.in_(competitor_ids))).all()
    }
    for comp_id, (pp, prev) in latest.items():
        comp = competitors.get(comp_id)
        if comp is None:
            continue
        change_pct = None
        if prev is not None and prev.price and pp.price:
            change_pct = round((pp.price - prev.price) / prev.price * 100, 2)
        result.append(
            CompetitorPrice(
                competitor_id=comp.id,
                competitor_name=comp.name,
                domain=comp.domain,
                price=pp.price,
                currency=pp.currency,
                stock_status=pp.stock_status,
                url=pp.url,
                captured_at=pp.captured_at,
                change_pct=change_pct,
            )
        )
    return result


@router.get("", response_model=list[ProductRead])
def list_products(
    team: CurrentTeamDep,
    session: SessionDep,
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    include_recommendation: bool = Query(default=True),
):
    query = select(Product).where(Product.team_id == team.id)
    if search:
        term = f"%{search}%"
        query = query.where(Product.name.ilike(term) | Product.sku.ilike(term) | Product.brand.ilike(term))
    if category:
        query = query.where(Product.category == category)
    if active is not None:
        query = query.where(Product.active.is_(active))
    products = session.exec(query.order_by(Product.name)).all()
    return [_to_read(session, p, include_recommendation=include_recommendation) for p in products]


@router.get("/categories", response_model=list[str])
def list_categories(team: CurrentTeamDep, session: SessionDep):
    rows = session.exec(select(Product.category).where(Product.team_id == team.id).distinct()).all()
    return sorted(c for c in rows if c)


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(product_id: int, team: CurrentTeamDep, session: SessionDep):
    product = _get_owned(session, team.id, product_id)
    base = _to_read(session, product, include_recommendation=True)
    return ProductDetail(
        **base.model_dump(),
        competitors=_competitor_prices(session, product_id),
    )


@router.post("", response_model=ProductRead, status_code=201)
def create_product(
    payload: ProductCreate,
    user: CurrentUserDep,
    team: CurrentTeamDep,
    session: SessionDep,
    request: Request,
):
    exists = session.exec(
        select(Product).where(Product.team_id == team.id, Product.sku == payload.sku)
    ).first()
    if exists is not None:
        raise HTTPException(status_code=409, detail="SKU già esistente")
    product = Product(**payload.model_dump(), team_id=team.id)
    session.add(product)
    session.commit()
    session.refresh(product)
    log(
        session,
        team_id=team.id,
        user_id=user.id,
        action="product.create",
        entity="product",
        entity_id=product.id,
        detail=f"{product.sku} — {product.name}",
        request=request,
    )
    session.commit()
    return _to_read(session, product)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    user: CurrentUserDep,
    team: CurrentTeamDep,
    session: SessionDep,
    request: Request,
):
    product = _get_owned(session, team.id, product_id)
    changes = payload.model_dump(exclude_unset=True)
    if "sku" in changes:
        dup = session.exec(
            select(Product).where(
                Product.team_id == team.id,
                Product.sku == changes["sku"],
                Product.id != product_id,
            )
        ).first()
        if dup is not None:
            raise HTTPException(status_code=409, detail="SKU già esistente")
    for key, value in changes.items():
        setattr(product, key, value)
    product.updated_at = utcnow()
    session.add(product)
    log(
        session,
        team_id=team.id,
        user_id=user.id,
        action="product.update",
        entity="product",
        entity_id=product.id,
        detail=", ".join(sorted(changes.keys())) or None,
        request=request,
    )
    session.commit()
    session.refresh(product)
    return _to_read(session, product, include_recommendation=True)


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int, user: CurrentUserDep, team: CurrentTeamDep, session: SessionDep, request: Request
):
    product = _get_owned(session, team.id, product_id)
    session.delete(product)
    log(
        session,
        team_id=team.id,
        user_id=user.id,
        action="product.delete",
        entity="product",
        entity_id=product_id,
        detail=product.name,
        request=request,
    )
    session.commit()


@router.get("/{product_id}/history", response_model=list[HistorySeries])
def product_history(
    product_id: int,
    team: CurrentTeamDep,
    session: SessionDep,
    days: int = Query(default=30, ge=1, le=365),
):
    _get_owned(session, team.id, product_id)

    cutoff = utcnow() - timedelta(days=days)
    points = session.exec(
        select(PricePoint)
        .where(PricePoint.product_id == product_id, PricePoint.captured_at >= cutoff)
        .order_by(PricePoint.competitor_id, PricePoint.captured_at)
    ).all()

    competitor_ids = {pp.competitor_id for pp in points}
    competitors = {
        c.id: c
        for c in session.exec(select(Competitor).where(Competitor.id.in_(competitor_ids))).all()
    }
    grouped: dict[int, HistorySeries] = {}
    for pp in points:
        comp = competitors.get(pp.competitor_id)
        if comp is None:
            continue
        series = grouped.setdefault(
            comp.id,
            HistorySeries(competitor_id=comp.id, competitor_name=comp.name, domain=comp.domain, points=[]),
        )
        series.points.append(HistoryPoint(captured_at=pp.captured_at, price=pp.price))

    return list(grouped.values())


@router.get("/{product_id}/recommendation", response_model=RepricingRecommendation)
def product_recommendation(product_id: int, team: CurrentTeamDep, session: SessionDep):
    product = _get_owned(session, team.id, product_id)
    return repricing_recommendation(session, product)
