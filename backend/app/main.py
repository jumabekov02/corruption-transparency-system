from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import contractors, departments
from app.core.config import settings

# The FastAPI application object. Uvicorn looks for this (app.main:app).
app = FastAPI(
    title="Public Procurement Risk Monitoring System",
    version="0.1.0",
    description="REST API for monitoring public procurement and surfacing risk indicators.",
)

# CORS = Cross-Origin Resource Sharing. The browser blocks a page served from
# localhost:5173 (frontend) from calling localhost:8000 (backend) unless the
# backend explicitly allows that origin. This middleware adds that permission.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness check: proves the API process is up and responding."""
    return {"status": "ok"}


# Register routers. The /api/v1 prefix gives every endpoint a versioned path,
# e.g. /api/v1/departments.
app.include_router(departments.router, prefix="/api/v1")
app.include_router(contractors.router, prefix="/api/v1")
