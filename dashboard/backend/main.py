from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import asyncio
from typing import Optional
import os

from config import settings
from database import init_db
from api.v1 import router as api_router
from api.v1.health import router as health_router, set_startup_complete
from api.v1.integrations import include_router as include_integrations_router
from services.auth_service import get_current_user
from core.logging_config import configure_logging, get_logger
from models import User
from integration.qa_framework_client import get_qa_test_suites
from middleware.apm import APMMiddleware, init_app_info
from middleware.security_headers import SecurityHeadersMiddleware
from middleware.rate_limit import RateLimitMiddleware
from middleware.semantic_cache_middleware import SemanticCacheMiddleware
from prometheus_client import make_asgi_app

# Configure structured logging
log_level = os.getenv("LOG_LEVEL", "INFO")
environment = os.getenv("ENVIRONMENT", "development")
configure_logging(log_level=log_level, environment=environment)
logger = get_logger(__name__)

app = FastAPI(
    title="QA-Framework Dashboard API",
    description="API para la dashboard unificada de QA-FRAMEWORK",
    version="0.1.0",
    openapi_url=None if environment == "production" else "/api/v1/openapi.json",
    docs_url=None if environment == "production" else "/api/v1/docs",
    redoc_url=None if environment == "production" else "/api/v1/redoc",
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

# Add Semantic Cache middleware (before APM so cached responses skip APM tracking)
app.add_middleware(SemanticCacheMiddleware)

# Add APM middleware
app.add_middleware(APMMiddleware)

# Include API routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")

# Include integration router
include_integrations_router(app)

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
    init_app_info(
        version="0.1.0",
        environment=settings.ENVIRONMENT
    )
    
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
        raise HTTPException(
            status_code=500, detail=f"Error connecting to QA-FRAMEWORK: {str(e)}"
        )


# Only run uvicorn directly when executed as script, not when imported
if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
