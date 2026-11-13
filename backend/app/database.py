from __future__ import annotations

import os
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.environ.get(
    "PRICELENS_DATABASE_URL",
    "sqlite:///./pricelens.db",
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    """Create tables if they do not exist yet."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Yield a database session, closing it when the request is done."""
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
