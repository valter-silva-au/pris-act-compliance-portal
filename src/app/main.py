"""FastAPI application for WA PRIS Act Compliance Portal."""

from fastapi import FastAPI

# Create FastAPI application instance
app = FastAPI(
    title="WA PRIS Act Compliance Portal",
    description="A compliance management system for WA Privacy and Responsible Information Sharing Act",
    version="0.1.0"
)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Status indicator showing the service is healthy
    """
    return {"status": "ok"}
