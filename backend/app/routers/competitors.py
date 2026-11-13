from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from ..audit import log
from ..database import SessionDep
from ..models import Competitor, PricePoint
from ..schemas import CompetitorCreate, CompetitorRead, CompetitorUpdate
from ..security import CurrentTeamDep, CurrentUserDep

router = APIRouter(prefix="/competitors", tags=["competitors"])


def _get_owned(session: SessionDep, team_id: int, competitor_id: int) -> Competitor:
    competitor = session.get(Competitor, competitor_id)
    if competitor is None or competitor.team_id != team_id:
        raise HTTPException(status_code=404, detail="Competitor non trovato")
    return competitor


def _to_read(session: SessionDep, competitor: Competitor) -> CompetitorRead:
    products_tracked = len(
        session.exec(
            select(PricePoint.product_id).where(PricePoint.competitor_id == competitor.id).distinct()
        ).all()
    )
    data = competitor.model_dump()
    data["products_tracked"] = products_tracked
    return CompetitorRead(**data)


@router.get("", response_model=list[CompetitorRead])
def list_competitors(team: CurrentTeamDep, session: SessionDep):
    competitors = session.exec(
        select(Competitor).where(Competitor.team_id == team.id).order_by(Competitor.name)
    ).all()
    return [_to_read(session, c) for c in competitors]


@router.post("", response_model=CompetitorRead, status_code=201)
def create_competitor(
    payload: CompetitorCreate,
    user: CurrentUserDep,
    team: CurrentTeamDep,
    session: SessionDep,
    request: Request,
):
    competitor = Competitor(**payload.model_dump(), team_id=team.id)
    session.add(competitor)
    session.commit()
    session.refresh(competitor)
    log(
        session,
        team_id=team.id,
        user_id=user.id,
        action="competitor.create",
        entity="competitor",
        entity_id=competitor.id,
        detail=f"{competitor.name} ({competitor.domain})",
        request=request,
    )
    session.commit()
    return _to_read(session, competitor)


@router.patch("/{competitor_id}", response_model=CompetitorRead)
def update_competitor(
    competitor_id: int,
    payload: CompetitorUpdate,
    user: CurrentUserDep,
    team: CurrentTeamDep,
    session: SessionDep,
    request: Request,
):
    competitor = _get_owned(session, team.id, competitor_id)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(competitor, key, value)
    session.add(competitor)
    log(
        session,
        team_id=team.id,
        user_id=user.id,
        action="competitor.update",
        entity="competitor",
        entity_id=competitor.id,
        detail=", ".join(sorted(changes.keys())) or None,
        request=request,
    )
    session.commit()
    session.refresh(competitor)
    return _to_read(session, competitor)


@router.delete("/{competitor_id}", status_code=204)
def delete_competitor(
    competitor_id: int,
    user: CurrentUserDep,
    team: CurrentTeamDep,
    session: SessionDep,
    request: Request,
):
    competitor = _get_owned(session, team.id, competitor_id)
    session.delete(competitor)
    log(
        session,
        team_id=team.id,
        user_id=user.id,
        action="competitor.delete",
        entity="competitor",
        entity_id=competitor_id,
        detail=competitor.name,
        request=request,
    )
    session.commit()
