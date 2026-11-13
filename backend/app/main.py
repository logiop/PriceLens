from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from .database import engine, init_db
from .routers import alerts, auth, competitors, dashboard, export, products, repricing, system
from .scheduler import start_scheduler, stop_scheduler
from .seed import seed_demo

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as session:
        seed_demo(session)
    start_scheduler()
    yield
    await stop_scheduler()


app = FastAPI(
    title="PriceLens",
    description="Competitive pricing intelligence — clone migliorato di Minderest.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    return response


for router in (
    auth.router,
    products.router,
    competitors.router,
    alerts.router,
    dashboard.router,
    repricing.router,
    export.router,
    system.router,
):
    app.include_router(router, prefix="/api")


if FRONTEND_DIST.exists():
    app.frontend("/", directory=str(FRONTEND_DIST))
