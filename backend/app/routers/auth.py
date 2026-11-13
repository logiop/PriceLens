from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from ..audit import log
from ..database import SessionDep
from ..models import Team, TeamMember, User
from ..schemas import TokenResponse, UserLogin, UserRead, UserRegister
from ..security import CurrentUserDep, create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _personal_team_name(email: str) -> str:
    handle = email.split("@")[0]
    return f"Workspace di {handle}"


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: UserRegister, session: SessionDep, request: Request):
    email = payload.email.lower().strip()
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email già registrata")

    user = User(email=email, password_hash=hash_password(payload.password))
    session.add(user)
    session.commit()
    session.refresh(user)

    # Every new account gets a personal team so the app is usable immediately.
    team = Team(name=_personal_team_name(email))
    session.add(team)
    session.commit()
    session.refresh(team)
    session.add(TeamMember(team_id=team.id, user_id=user.id, role="owner"))
    log(
        session,
        team_id=team.id,
        user_id=user.id,
        action="auth.register",
        entity="user",
        entity_id=user.id,
        request=request,
    )
    session.commit()

    return TokenResponse(access_token=create_access_token(user.id), user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, session: SessionDep, request: Request):
    email = payload.email.lower().strip()
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    membership = session.exec(
        select(TeamMember).where(TeamMember.user_id == user.id).order_by(TeamMember.id)
    ).first()
    if membership is not None:
        log(
            session,
            team_id=membership.team_id,
            user_id=user.id,
            action="auth.login",
            entity="user",
            entity_id=user.id,
            request=request,
        )
        session.commit()

    return TokenResponse(access_token=create_access_token(user.id), user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(user: CurrentUserDep):
    return user
