from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from ..analytics import competitor_name
from ..database import SessionDep
from ..models import Alert, Product
from ..schemas import AlertRead
from ..security import CurrentUserDep

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _to_read(session: SessionDep, alert: Alert) -> AlertRead:
    product = session.get(Product, alert.product_id)
    data = alert.model_dump()
    data["product_name"] = product.name if product else None
    data["competitor_name"] = competitor_name(session, alert.competitor_id)
    return AlertRead(**data)


@router.get("", response_model=list[AlertRead])
def list_alerts(
    user: CurrentUserDep,
    session: SessionDep,
    unread: bool | None = Query(default=None),
    severity: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    query = select(Alert).where(Alert.user_id == user.id)
    if unread is not None:
        query = query.where(Alert.read.is_(not unread))
    if severity:
        query = query.where(Alert.severity == severity)
    alerts = session.exec(query.order_by(Alert.created_at.desc()).limit(limit)).all()
    return [_to_read(session, a) for a in alerts]


@router.get("/counts")
def alert_counts(user: CurrentUserDep, session: SessionDep):
    alerts = session.exec(select(Alert).where(Alert.user_id == user.id)).all()
    total = len(alerts)
    unread = sum(1 for a in alerts if not a.read)
    critical = sum(1 for a in alerts if a.severity == "critical" and not a.read)
    return {"total": total, "unread": unread, "critical_unread": critical}


@router.post("/{alert_id}/read", response_model=AlertRead)
def mark_read(alert_id: int, user: CurrentUserDep, session: SessionDep):
    alert = session.get(Alert, alert_id)
    if alert is None or alert.user_id != user.id:
        raise HTTPException(status_code=404, detail="Alert non trovato")
    alert.read = True
    session.add(alert)
    session.commit()
    session.refresh(alert)
    return _to_read(session, alert)


@router.post("/read-all")
def mark_all_read(user: CurrentUserDep, session: SessionDep):
    alerts = session.exec(
        select(Alert).where(Alert.user_id == user.id, Alert.read.is_(False))
    ).all()
    for alert in alerts:
        alert.read = True
        session.add(alert)
    session.commit()
    return {"marked_read": len(alerts)}
