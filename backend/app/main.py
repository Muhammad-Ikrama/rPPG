"""
FastAPI Cloud Backend Entrypoint for rPPG Vital Signs Monitoring System.
"""

from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.db.session import init_db
from app.api.auth import router as auth_router
from app.api.subjects import router as subjects_router
from app.api.measurements import router as measurements_router
from app.api.stream import router as stream_router
from app.api.reports import router as reports_router
from app.api.datasets import router as datasets_router
from app.api.dl_models import router as dl_models_router
from app.api.cohort import router as cohort_router
from app.api.sync import router as sync_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB tables
    await init_db()
    yield
    # Shutdown logic if any


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Cloud-connected biomedical backend for non-contact vital sign monitoring "
        "via facial video and Remote Photoplethysmography (rPPG). "
        "Supports Heart Rate (HR), Respiratory Rate (RR), SpO2, and Experimental Blood Pressure."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(subjects_router, prefix=settings.API_V1_PREFIX)
app.include_router(measurements_router, prefix=settings.API_V1_PREFIX)
app.include_router(stream_router, prefix=settings.API_V1_PREFIX)
app.include_router(reports_router, prefix=settings.API_V1_PREFIX)
app.include_router(datasets_router, prefix=settings.API_V1_PREFIX)
app.include_router(dl_models_router, prefix=settings.API_V1_PREFIX)
app.include_router(cohort_router, prefix=settings.API_V1_PREFIX)
app.include_router(sync_router, prefix=settings.API_V1_PREFIX)

# Healthcheck
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "engine": "POS (Wang et al. 2017)",
    }

# Mount Web Application Static Files if web directory exists
web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "web"))
if os.path.exists(web_dir):
    app.mount("/app", StaticFiles(directory=web_dir, html=True), name="web_app")

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return RedirectResponse(url="/app/index.html")
