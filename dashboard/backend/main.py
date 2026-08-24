import os

from database import init_db
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from integration.qa_framework_client import get_qa_test_suites
from middleware.apm import APMMiddleware, init_app_info
from middleware.rate_limit import RateLimitMiddleware
from middleware.security_headers import SecurityHeadersMiddleware
from models import User
from prometheus_client import make_asgi_app
from services.auth_service import get_current_user, get_qa_visual_principal

from api.v1 import router as api_router
from api.v1.health import router as health_router
from api.v1.health import set_startup_complete
from api.v1.integrations import include_router as include_integrations_router
from config import settings
from core.logging_config import configure_logging, get_logger
from src.infrastructure.qa_visual import create_qa_visual_router

# Configure structured logging
log_level = os.getenv("LOG_LEVEL", "INFO")
environment = os.getenv("ENVIRONMENT", "development")
configure_logging(log_level=log_level, environment=environment)
logger = get_logger(__name__)

app = FastAPI(
    title="QA-Framework Dashboard API",
    description="API para la dashboard unificada de QA-FRAMEWORK",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:8080",
        "https://frontend-phi-three-52.vercel.app",  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # expose_headers=["Access-Control-Allow-Origin"]
)

# Add Security Headers middleware (before other middleware)
app.add_middleware(SecurityHeadersMiddleware)

# Add Rate Limiting middleware
app.add_middleware(RateLimitMiddleware)

# Add APM middleware
app.add_middleware(APMMiddleware)

# Include API routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")

# Include integration router
include_integrations_router(app)

# QA Visual router (Fase C) — vendored copy under dashboard/backend/src,
# mounted behind the dashboard auth (S-1) with owner scoping (S-1R):
# every endpoint requires a valid JWT via Depends(get_current_user) and
# reports are scoped to the calling user (QAVisualPrincipal.owner =
# username); superusers (is_superuser) bypass the scoping as admins.
# Reports persisted before owner-scoping are admin-only. The mount still
# requires an explicit deploy opt-in with QA_VISUAL_ENABLED=1.
if os.getenv("QA_VISUAL_ENABLED") == "1":
    app.include_router(
        create_qa_visual_router(
            dependencies=[Depends(get_current_user)],
            get_current_principal=get_qa_visual_principal,
        )
    )

# Accuracy testing router (card c9825844) — vendored copy under
# dashboard/backend/src, same opt-in pattern as qa-visual. Security
# contracts: L-1 per-tenant salt derived server-side (ACCURACY_SPLIT_SECRET,
# required — the router factory fails closed on an empty secret) and L-2
# owner-scoped resources with to_dict_full() served to superusers only.
if os.getenv("ACCURACY_TESTING_ENABLED") == "1":
    from src.infrastructure.accuracy_testing.endpoint import create_accuracy_router
    from src.infrastructure.accuracy_testing.security import AccuracyPrincipal

    def _accuracy_principal(user: User = Depends(get_current_user)) -> AccuracyPrincipal:
        return AccuracyPrincipal(
            owner=str(user.tenant_id) if user.tenant_id else f"user-{user.id}",
            is_admin=bool(user.is_superuser),
        )

    app.include_router(
        create_accuracy_router(
            principal_dependency=_accuracy_principal,
            split_secret=os.getenv("ACCURACY_SPLIT_SECRET", ""),
        )
    )

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.on_event("startup")
async def startup_event():
    """Initialize database and other resources on startup"""
    logger.info("Initializing QA-Framework Dashboard...")
    await init_db()
    set_startup_complete()

    # Initialize APM
    init_app_info(version="0.1.0", environment=settings.ENVIRONMENT)

    logger.info("QA-Framework Dashboard initialized successfully")


@app.get("/")
async def root():
    return {"message": "QA-Framework Dashboard API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "qa-framework-dashboard-api"}


@app.get("/api/v1/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/api/v1/integration/qa-framework/suites")
async def get_qa_framework_suites(current_user: User = Depends(get_current_user)):
    """Get available test suites from QA-FRAMEWORK"""
    try:
        suites = await get_qa_test_suites()
        return {"suites": suites}
    except Exception as e:
        logger.error(f"Error getting QA-FRAMEWORK suites: {e}")
        raise HTTPException(status_code=500, detail=f"Error connecting to QA-FRAMEWORK: {str(e)}")


# Only run uvicorn directly when executed as script, not when imported
if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
