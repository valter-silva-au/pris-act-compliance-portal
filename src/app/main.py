"""FastAPI application for WA PRIS Act Compliance Portal."""

from fastapi import FastAPI
from src.app.auth import router as auth_router
from src.app.database import init_db

# Create FastAPI application instance
app = FastAPI(
    title="WA PRIS Act Compliance Portal",
    description="A compliance management system for WA Privacy and Responsible Information Sharing Act",
    version="0.1.0"
)

# Initialize database tables on startup
@app.on_event("startup")
def startup_event():
    """Initialize database tables on application startup."""
    init_db()

# Include routers
app.include_router(auth_router)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Status indicator showing the service is healthy
    """
    return {"status": "ok"}
