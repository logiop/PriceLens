from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from ..analytics import repricing_recommendation
from ..audit import log
from ..database import SessionDep
from ..models import Product
from ..models import utcnow
from ..schemas import ApplyRecommendation, RepricingPreview, RepricingRecommendation
from ..security import CurrentTeamDep, CurrentUserDep

router = APIRouter(prefix="/repricing", tags=["repricing"])


@router.get("/preview", response_model=RepricingPreview)
def preview(team: CurrentTeamDep, session: SessionDep, only_actionable: bool = False):
    products = session.exec(
        select(Product).where(Product.team_id == team.id, Product.active.is_(True))
    ).all()
    recommendations = [repricing_recommendation(session, p) for p in products]
    if only_actionable:
        recommendations = [r for r in recommendations if abs(r.delta_pct) >= 0.5]
    recommendations.sort(key=lambda r: r.delta_pct, reverse=True)

    impact = sum((r.suggested_price - r.current_price) for r in recommendations)
    return RepricingPreview(
        recommendations=recommendations,
        total_potential_margin_impact=round(impact, 2),
    )


@router.post("/apply", response_model=RepricingRecommendation)
def apply(
    payload: ApplyRecommendation,
    user: CurrentUserDep,
    team: CurrentTeamDep,
    session: SessionDep,
    request: Request,
):
    product = session.get(Product, payload.product_id)
    if product is None or product.team_id != team.id:
        raise HTTPException(status_code=404, detail="Prodotto non trovato")
    old_price = product.current_price
    product.current_price = payload.suggested_price
    product.updated_at = utcnow()
    session.add(product)
    log(
        session,
        team_id=team.id,
        user_id=user.id,
        action="repricing.apply",
        entity="product",
        entity_id=product.id,
        detail=f"{old_price:.2f} → {payload.suggested_price:.2f}",
        request=request,
    )
    session.commit()
    session.refresh(product)
    return repricing_recommendation(session, product)
