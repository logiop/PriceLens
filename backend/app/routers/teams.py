from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from ..audit import log
from ..database import SessionDep
from ..models import Team, TeamMember, User
from ..schemas import (
    TeamCreate,
    TeamMemberCreate,
    TeamMemberRead,
    TeamRead,
)
from ..security import CurrentUserDep

router = APIRouter(prefix="/teams", tags=["teams"])

MANAGER_ROLES = {"owner", "admin"}


def _membership(session: SessionDep, team_id: int, user_id: int) -> TeamMember | None:
    return session.exec(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    ).first()


def _require_member(session: SessionDep, team_id: int, user_id: int) -> TeamMember:
    membership = _membership(session, team_id, user_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Team non trovato")
    return membership


def _require_manager(session: SessionDep, team_id: int, user_id: int) -> TeamMember:
    membership = _require_member(session, team_id, user_id)
    if membership.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Permesso insufficiente")
    return membership


def _to_read(session: SessionDep, team: Team, role: str) -> TeamRead:
    member_count = len(
        session.exec(select(TeamMember).where(TeamMember.team_id == team.id)).all()
    )
    return TeamRead(
        id=team.id,
        name=team.name,
        role=role,
        member_count=member_count,
        created_at=team.created_at,
    )


@router.get("", response_model=list[TeamRead])
def list_teams(user: CurrentUserDep, session: SessionDep):
    memberships = session.exec(
        select(TeamMember).where(TeamMember.user_id == user.id).order_by(TeamMember.id)
    ).all()
    teams = {t.id: t for t in session.exec(select(Team)).all()}
    result: list[TeamRead] = []
    for m in memberships:
        team = teams.get(m.team_id)
        if team is not None:
            result.append(_to_read(session, team, m.role))
    return result


@router.post("", response_model=TeamRead, status_code=201)
def create_team(payload: TeamCreate, user: CurrentUserDep, session: SessionDep, request: Request):
    team = Team(name=payload.name.strip())
    session.add(team)
    session.commit()
    session.refresh(team)
    session.add(TeamMember(team_id=team.id, user_id=user.id, role="owner"))
    log(
        session,
        team_id=team.id,
        user_id=user.id,
        action="team.create",
        entity="team",
        entity_id=team.id,
        detail=team.name,
        request=request,
    )
    session.commit()
    return _to_read(session, team, "owner")


@router.patch("/{team_id}", response_model=TeamRead)
def rename_team(
    team_id: int, payload: TeamCreate, user: CurrentUserDep, session: SessionDep, request: Request
):
    membership = _require_manager(session, team_id, user.id)
    team = session.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team non trovato")
    team.name = payload.name.strip()
    session.add(team)
    log(
        session,
        team_id=team.id,
        user_id=user.id,
        action="team.rename",
        entity="team",
        entity_id=team.id,
        detail=team.name,
        request=request,
    )
    session.commit()
    session.refresh(team)
    return _to_read(session, team, membership.role)


@router.get("/{team_id}/members", response_model=list[TeamMemberRead])
def list_members(team_id: int, user: CurrentUserDep, session: SessionDep):
    _require_member(session, team_id, user.id)
    members = session.exec(select(TeamMember).where(TeamMember.team_id == team_id)).all()
    users = {u.id: u for u in session.exec(select(User)).all()}
    result: list[TeamMemberRead] = []
    for m in members:
        u = users.get(m.user_id)
        if u is not None:
            result.append(
                TeamMemberRead(
                    user_id=u.id, email=u.email, role=m.role, created_at=m.created_at
                )
            )
    return result


@router.post("/{team_id}/members", response_model=TeamMemberRead, status_code=201)
def add_member(
    team_id: int,
    payload: TeamMemberCreate,
    user: CurrentUserDep,
    session: SessionDep,
    request: Request,
):
    _require_manager(session, team_id, user.id)
    email = payload.email.lower().strip()
    target = session.exec(select(User).where(User.email == email)).first()
    if target is None:
        raise HTTPException(
            status_code=404,
            detail="Utente non registrato: deve creare un account prima di essere aggiunto",
        )
    if _membership(session, team_id, target.id) is not None:
        raise HTTPException(status_code=409, detail="Utente già membro del team")
    member = TeamMember(team_id=team_id, user_id=target.id, role=payload.role)
    session.add(member)
    log(
        session,
        team_id=team_id,
        user_id=user.id,
        action="team.member_add",
        entity="user",
        entity_id=target.id,
        detail=f"{email} ({payload.role})",
        request=request,
    )
    session.commit()
    session.refresh(member)
    return TeamMemberRead(
        user_id=target.id, email=target.email, role=member.role, created_at=member.created_at
    )


@router.delete("/{team_id}/members/{member_user_id}", status_code=204)
def remove_member(
    team_id: int,
    member_user_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    request: Request,
):
    _require_manager(session, team_id, user.id)
    member = _membership(session, team_id, member_user_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Membro non trovato")
    if member.role == "owner":
        raise HTTPException(status_code=400, detail="Non puoi rimuovere il proprietario")
    session.delete(member)
    log(
        session,
        team_id=team_id,
        user_id=user.id,
        action="team.member_remove",
        entity="user",
        entity_id=member_user_id,
        request=request,
    )
    session.commit()
