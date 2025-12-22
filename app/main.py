"""
Main FastAPI Application with Database Logging and API Key Authentication
"""

import os
import logging

from fastapi import FastAPI, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from app.config import settings
from app.services.common.database_service import db_service
from app.services.common.db_logger_service import db_logger_service
from app.middleware.auth_middleware import APIKeyMiddleware

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


# Define API Key security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# Create FastAPI app
app = FastAPI(
    title="Assessment AI Service",
    description="Analysis API. **Authentication Required**: Add your API key using the 'Authorize' button below.",
    version="1.0.0",
    docs_url=None,  # Disable default docs to customize
    redoc_url=None,  # Disable default redoc to customize
)

# CORS middleware (add before auth middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  #Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add API Key Authentication Middleware
app.add_middleware(APIKeyMiddleware)


# Custom OpenAPI schema with API Key security
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Assessment AI Service",
        version="1.0.0",
        description="Analysis API with API Key Authentication",
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Enter your API key"
        }
    }
    
    # Apply security globally to all endpoints except excluded ones
    excluded_paths = ["/health", "/docs", "/redoc", "/openapi.json"]
    for path, path_item in openapi_schema["paths"].items():
        if path not in excluded_paths:
            for method in path_item.values():
                if isinstance(method, dict) and "security" not in method:
                    method["security"] = [{"APIKeyHeader": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Custom Swagger UI with persistence
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Assessment AI Service - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
        swagger_ui_parameters={
            "persistAuthorization": True,  # Remember API key in browser
            "displayRequestDuration": True,
            "filter": True,
        }
    )


# Custom ReDoc
@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    from fastapi.openapi.docs import get_redoc_html
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="Assessment AI Service - ReDoc"
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

        logger.info("✅ All services initialized successfully!")
        logger.info("🔐 API Key authentication is enabled")
        logger.info(
            f"📚 API docs at http://{settings.API_HOST}:{settings.API_PORT}/docs"
        )

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down AI Microservice...")


# Include routers
app.include_router(score_analysis_router)


# Root Endpoint (requires API key)
@app.get("/", summary="API Root", tags=["General"])
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


# Health Check Endpoint (no API key required)
@app.get("/health", summary="Health Check", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "database": settings.DB_NAME,
    }
