from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ghost",
        description="Supply chain security monitor",
        version="0.1.0",
        lifespan=lifespan,
    )

    import os
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.routers import (
        alerts, analyses, findings, health, packages,
        versions, vulnerabilities, vulnerability_scans, webhooks,
    )

    app.include_router(health.router)
    app.include_router(packages.router, prefix="/api/v1")
    app.include_router(versions.router, prefix="/api/v1")
    app.include_router(analyses.router, prefix="/api/v1")
    app.include_router(findings.router, prefix="/api/v1")
    app.include_router(alerts.router, prefix="/api/v1")
    app.include_router(vulnerability_scans.router, prefix="/api/v1")
    app.include_router(vulnerabilities.router, prefix="/api/v1")
    app.include_router(webhooks.router, prefix="/api/v1")

    return app
