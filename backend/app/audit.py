from __future__ import annotations

from fastapi import Request
from sqlmodel import Session

from .models import AuditLog


def log(
    session: Session,
    *,
    team_id: int,
    user_id: int | None = None,
    action: str,
    entity: str | None = None,
    entity_id: int | None = None,
    detail: str | None = None,
    request: Request | None = None,
) -> None:
    """Add an audit entry to the session (the caller commits)."""
    ip = None
    if request is not None and request.client is not None:
        ip = request.client.host
    session.add(
        AuditLog(
            team_id=team_id,
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            detail=detail,
            ip=ip,
        )
    )
