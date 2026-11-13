from __future__ import annotations

from fastapi import APIRouter, Query
from sqlmodel import select

from ..database import SessionDep
from ..models import AuditLog, User
from ..schemas import AuditLogRead
from ..security import CurrentTeamDep

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
def list_audit(
    team: CurrentTeamDep,
    session: SessionDep,
    limit: int = Query(default=100, ge=1, le=500),
):
    entries = session.exec(
        select(AuditLog)
        .where(AuditLog.team_id == team.id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    ).all()
    users = {u.id: u for u in session.exec(select(User)).all()}
    result: list[AuditLogRead] = []
    for e in entries:
        data = e.model_dump()
        data["user_email"] = users[e.user_id].email if e.user_id in users else None
        result.append(AuditLogRead(**data))
    return result
