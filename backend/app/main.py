from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.core.db import init_db
from app.routes import auth, profile, schemes, vault, chat, analytics

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multi-Agent platform for autonomous government benefits discovery and application prep.",
    version="1.0.0"
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve upload files
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.on_event("startup")
def on_startup():
    # Initialize DB tables and seed schemes
    init_db()

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "api_docs": "/docs",
        "version": "1.0.0"
    }

# Include routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(schemes.router)
app.include_router(vault.router)
app.include_router(chat.router)
app.include_router(analytics.router)
