from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import select

from .database import SessionDep
from .models import Team, TeamMember, User

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("PRICELENS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days

_PBKDF2_ITERATIONS = 600_000

_bearer = HTTPBearer(auto_error=False)


def _load_or_create_secret() -> str:
    """Resolve the JWT signing key.

    Priority: env var → persisted key file → newly generated (and persisted) key.
    Persisting the key keeps sessions valid across restarts and lets several
    workers share the same signing key.
    """
    env_key = os.environ.get("PRICELENS_SECRET_KEY")
    if env_key:
        return env_key

    key_path = Path(
        os.environ.get(
            "PRICELENS_SECRET_KEY_FILE",
            Path(__file__).resolve().parent.parent / ".secret_key",
        )
    )
    try:
        if key_path.exists():
            stored = key_path.read_text(encoding="utf-8").strip()
            if stored:
                return stored
        new_key = secrets.token_hex(32)
        key_path.write_text(new_key + "\n", encoding="utf-8")
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
        return new_key
    except OSError as exc:  # read-only FS, permissions, sandbox…
        warnings.warn(
            f"Impossibile persistere la chiave JWT in {key_path} ({exc}); "
            "verrà usata una chiave effimera e le sessioni decadranno al riavvio. "
            "Imposta PRICELENS_SECRET_KEY in produzione.",
            RuntimeWarning,
        )
        return secrets.token_hex(32)


SECRET_KEY = _load_or_create_secret()


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256 and a per-user random salt."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check of a password against a stored hash."""
    try:
        _algo, iterations, salt, expected = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(dk.hex(), expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, expires_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: SessionDep,
) -> User:
    """Resolve the authenticated user from the Authorization: Bearer header."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non autenticato",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token non valido o scaduto",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utente non trovato",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_current_team(
    user: CurrentUserDep,
    session: SessionDep,
    x_team_id: Annotated[int | None, Header(alias="X-Team-Id")] = None,
) -> Team:
    """Resolve the active team: explicit X-Team-Id header or the user's first team."""
    if x_team_id is not None:
        membership = session.exec(
            select(TeamMember).where(
                TeamMember.team_id == x_team_id,
                TeamMember.user_id == user.id,
            )
        ).first()
        team = session.get(Team, x_team_id)
        if membership is None or team is None:
            raise HTTPException(status_code=403, detail="Non appartieni a questo team")
        return team

    membership = session.exec(
        select(TeamMember).where(TeamMember.user_id == user.id).order_by(TeamMember.id)
    ).first()
    if membership is None:
        raise HTTPException(status_code=400, detail="Nessun team associato all'utente")
    team = session.get(Team, membership.team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team non trovato")
    return team


CurrentTeamDep = Annotated[Team, Depends(get_current_team)]
