"""FastAPI application for WA PRIS Act Compliance Portal."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.app.auth import router as auth_router
from src.app.ipp import router as ipp_router
from src.app.routes.web import router as web_router
from src.app.reports import router as reports_router
from src.app.database import init_db, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown.

    Handles database initialization and optional demo data seeding.
    """
    # Startup
    init_db()

    # Seed demo data if SEED_DEMO environment variable is set to 1
    if os.getenv("SEED_DEMO") == "1":
        print("\nSEED_DEMO=1 detected. Seeding demo data...")
        from src.app.seed import seed_demo_data
        db = next(get_db())
        try:
            seed_demo_data(db)
        finally:
            db.close()

    yield

    # Shutdown (cleanup if needed)


# Create FastAPI application instance
app = FastAPI(
    title="WA PRIS Act Compliance Portal",
    description="A compliance management system for WA Privacy and Responsible Information Sharing Act",
    version="0.1.0",
    lifespan=lifespan
)

# Include routers
app.include_router(web_router)
app.include_router(auth_router)
app.include_router(ipp_router)
app.include_router(reports_router)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Status indicator showing the service is healthy
    """
    return {"status": "ok"}
