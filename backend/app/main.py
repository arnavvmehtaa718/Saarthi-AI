from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.base import get_ai_client
from app.core.config import settings
from app.core.db import init_db
from app.routes import analytics, auth, chat, profile, schemes, vault


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Multi-agent platform for government-benefit discovery, deterministic eligibility "
        "checks, document readiness, and application preparation."
    ),
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    ai = get_ai_client()
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "api_docs": "/docs",
        "version": "1.1.0",
        "ai_mode": ai.status()["mode"],
    }


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.get("/ai/status")
def ai_status():
    return get_ai_client().status()


app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(schemes.router)
app.include_router(vault.router)
app.include_router(chat.router)
app.include_router(analytics.router)
