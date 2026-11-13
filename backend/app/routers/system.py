from __future__ import annotations

from fastapi import APIRouter, Request

from ..audit import log
from ..collector import collect_round
from ..database import SessionDep
from ..scheduler import status as scheduler_status
from ..schemas import CollectResult
from ..security import CurrentTeamDep, CurrentUserDep

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "pricelens"}


@router.post("/collect", response_model=CollectResult)
def trigger_collect(
    user: CurrentUserDep,
    team: CurrentTeamDep,
    session: SessionDep,
    request: Request,
):
    """Run a price-collection round now for the current team's products."""
    result = collect_round(session, team_id=team.id)
    log(
        session,
        team_id=team.id,
        user_id=user.id,
        action="collect.run",
        entity="team",
        entity_id=team.id,
        detail=f"collected={result.collected} alerts={result.alerts_created}",
        request=request,
    )
    session.commit()
    return result


@router.get("/scheduler/status")
def scheduler_status_endpoint(_user: CurrentUserDep):
    """Operational info about the background collection scheduler."""
    return scheduler_status()
