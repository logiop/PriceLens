from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from sqlmodel import Session, select

from .collector import collect_round
from .database import engine
from .models import User

INTERVAL_SECONDS = int(os.environ.get("PRICELENS_COLLECT_INTERVAL_SECONDS", "300"))
ENABLED = os.environ.get("PRICELENS_SCHEDULER_ENABLED", "1").lower() not in ("0", "false", "no")


class SchedulerState:
    def __init__(self) -> None:
        self.task: asyncio.Task | None = None
        self.running: bool = False
        self.last_run: datetime | None = None
        self.last_error: str | None = None
        self.last_result: dict | None = None


state = SchedulerState()


def _collect_all_users() -> dict:
    """Run one collection round for every user (blocking; called in a thread)."""
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        totals = {"collected": 0, "alerts_created": 0, "skipped": 0, "errors": 0}
        for user in users:
            result = collect_round(session, user_id=user.id)
            totals["collected"] += result.collected
            totals["alerts_created"] += result.alerts_created
            totals["skipped"] += result.skipped
            totals["errors"] += result.errors
        return totals


async def _loop() -> None:
    while True:
        await asyncio.sleep(INTERVAL_SECONDS)
        state.running = True
        state.last_run = datetime.now(timezone.utc)
        try:
            state.last_result = await asyncio.to_thread(_collect_all_users)
            state.last_error = None
        except Exception as exc:  # noqa: BLE001 - keep the loop alive on any error
            state.last_error = str(exc)
            state.last_result = None
        finally:
            state.running = False


def start_scheduler() -> None:
    if not ENABLED:
        return
    state.task = asyncio.create_task(_loop())


async def stop_scheduler() -> None:
    if state.task is not None:
        state.task.cancel()
        try:
            await state.task
        except asyncio.CancelledError:
            pass


def status() -> dict:
    return {
        "enabled": ENABLED,
        "interval_seconds": INTERVAL_SECONDS,
        "running": state.running,
        "last_run": state.last_run,
        "last_error": state.last_error,
        "last_result": state.last_result,
    }
