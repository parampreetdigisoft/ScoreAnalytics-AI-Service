"""
Main FastAPI Application with Database Logging
"""

import os
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.config import settings
from app.services.common.database_service import db_service
from app.services.common.db_logger_service import db_logger_service

# Import routers
from app.routers.score_analysis_router import router as score_analysis_router


# Configure logging to database
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# Add database handler
db_handler = db_logger_service.get_handler()
db_handler.setLevel(logging.ERROR)
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
db_handler.setFormatter(formatter)
logger.addHandler(db_handler)

# Also configure root logger to use database
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(db_handler)


# Create FastAPI app
app = FastAPI(
    title="Assessment AI Service",
    description="Text-to-SQL and NLP Processing API",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch all unhandled exceptions and log them to database
    """
    logger.error(
        f"Unhandled exception at {request.url.path}",
        exc_info=exc,
        extra={
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else "unknown"
        }
    )
    
    # Also use direct service call for critical errors
    db_logger_service.log_exception(
        "ERROR",
        f"Unhandled exception at {request.method} {request.url.path}",
        exc
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": request.url.path
        }
    )


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting AI Microservice...")
    
    try:
        # Test database connection
        logger.info("Testing database connection...")
        db_connected = db_service.test_connection()
        
        if not db_connected:
            logger.warning("⚠️ Database connection failed - some features may not work")
            db_logger_service.log_message(
                "WARNING",
                "Database connection failed during startup"
            )

        logger.info("✅ All services initialized successfully!")
        logger.info(
            f"📚 API docs at http://{settings.API_HOST}:{settings.API_PORT}/docs"
        )

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}", exc_info=True)
        db_logger_service.log_exception("CRITICAL", "Application startup failed", e)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down AI Microservice...")


# Include routers
app.include_router(score_analysis_router)


# Root Endpoint
@app.get("/", summary="API Root")
async def root():
    return {
        "service": "Assessment AI Service",
        "status": "running",
        "model_in_use": settings.LLM_PROVIDER,
        "routes": {
            "health_check": "/health",
            "documentation": f"http://{settings.API_HOST}:{settings.API_PORT}/docs",
            "openapi_json": f"http://{settings.API_HOST}/openapi.json",
        },
    }


# Health Check Endpoint
@app.get("/health", summary="Health Check")
async def health_check():
    return {
        "status": "healthy",
        "database": settings.DB_NAME,
    }


# ASGI Server Entry
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
    )