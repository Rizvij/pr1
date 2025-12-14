"""ProRyx Property Management System - Main Application Entry Point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .core.exceptions import ProRyxException
from .core.logging import RequestIdMiddleware, get_logger, setup_logging

# Import routers
from .modules.auth import router as auth_router
from .modules.property_management import (
    categories_router as unit_categories_router,
)
from .modules.property_management import (
    router as properties_router,
)
from .modules.property_management import (
    units_router,
)
from .modules.tenant_management import (
    doc_types_router as document_types_router,
)
from .modules.tenant_management import (
    router as tenants_router,
)
from .modules.vendor_management import (
    leases_router as vendor_leases_router,
)
from .modules.vendor_management import (
    router as vendors_router,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting ProRyx application...")
    setup_logging()
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.app_debug}")
    yield
    # Shutdown
    logger.info("Shutting down ProRyx application...")


# Create FastAPI application
app = FastAPI(
    title="ProRyx API",
    description="Property Management System for Short-Term Rentals",
    version="1.0.0",
    docs_url="/api/docs" if settings.app_debug else None,
    redoc_url="/api/redoc" if settings.app_debug else None,
    openapi_url="/api/openapi.json" if settings.app_debug else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID middleware for request tracing
app.add_middleware(RequestIdMiddleware)


# Global exception handler
@app.exception_handler(ProRyxException)
async def proryx_exception_handler(request: Request, exc: ProRyxException):
    """Handle ProRyx-specific exceptions."""
    # Get status code from exception or default to 400
    status_code = getattr(exc, "status_code", 400)
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": exc.message,
            "error": exc.message,
            "data": None,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc) if settings.app_debug else "Internal server error",
            "data": None,
        },
    )


# Health check endpoint
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "env": settings.app_env,
    }


# Register routers with /api prefix
API_PREFIX = "/api"

# Auth routes
app.include_router(auth_router, prefix=API_PREFIX)

# Property Management routes (EP-01)
app.include_router(properties_router, prefix=API_PREFIX)
app.include_router(units_router, prefix=API_PREFIX)
app.include_router(unit_categories_router, prefix=API_PREFIX)

# Vendor Management routes (EP-02)
app.include_router(vendors_router, prefix=API_PREFIX)
app.include_router(vendor_leases_router, prefix=API_PREFIX)

# Tenant Management routes (EP-03)
app.include_router(tenants_router, prefix=API_PREFIX)
app.include_router(document_types_router, prefix=API_PREFIX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "proryx_backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_debug,
    )
