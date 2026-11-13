from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from ..analytics import repricing_recommendation
from ..database import SessionDep
from ..models import Product
from ..models import utcnow
from ..schemas import ApplyRecommendation, RepricingPreview, RepricingRecommendation
from ..security import CurrentUserDep

router = APIRouter(prefix="/repricing", tags=["repricing"])


@router.get("/preview", response_model=RepricingPreview)
def preview(user: CurrentUserDep, session: SessionDep, only_actionable: bool = False):
    products = session.exec(
        select(Product).where(Product.user_id == user.id, Product.active.is_(True))
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
def apply(payload: ApplyRecommendation, user: CurrentUserDep, session: SessionDep):
    product = session.get(Product, payload.product_id)
    if product is None or product.user_id != user.id:
        raise HTTPException(status_code=404, detail="Prodotto non trovato")
    product.current_price = payload.suggested_price
    product.updated_at = utcnow()
    session.add(product)
    session.commit()
    session.refresh(product)
    return repricing_recommendation(session, product)
