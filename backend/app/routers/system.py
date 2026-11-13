from __future__ import annotations

from fastapi import APIRouter

from ..collector import collect_round
from ..database import SessionDep
from ..scheduler import status as scheduler_status
from ..schemas import CollectResult
from ..security import CurrentUserDep

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "pricelens"}


@router.post("/collect", response_model=CollectResult)
def trigger_collect(user: CurrentUserDep, session: SessionDep):
    """Run a price-collection round now for the current user's products."""
    return collect_round(session, user_id=user.id)


@router.get("/scheduler/status")
def scheduler_status_endpoint(_user: CurrentUserDep):
    """Operational info about the background collection scheduler."""
    return scheduler_status()
