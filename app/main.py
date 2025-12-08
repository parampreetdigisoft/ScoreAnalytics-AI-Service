"""
Main FastAPI Application
"""
import os
import logging
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import settings
from app.services.common.database_service import db_service
# Import routers
from app.routers.score_analysis_router import router as score_analysis_router
# Add your other routers here
# from app.routers.chat import router as chat_router
# from app.routers.summarizer import router as summarizer_router

# Configure logging


# Get your project directory (folder where this file is located)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Create Logs folder inside your project (if not exists)
LOG_DIR = os.path.join(BASE_DIR, "Logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Full path: <your_project>/Logs/error.log
LOG_FILE = os.path.join(LOG_DIR, "error.log")

# Configure rotating error log
handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=1_000_000,   # 1 MB
    backupCount=3
)
handler.setLevel(logging.ERROR)
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
handler.setFormatter(formatter)

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
logger.addHandler(handler)


# Create FastAPI app
app = FastAPI(
    title="AI Microservice API",
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

        # # Initialize text-to-SQL service
        # logger.info("Initializing Text-to-SQL service...")
        # await text_to_sql_service.initialize()

        logger.info("✅ All services initialized successfully!")
        logger.info(
            f"📚 API docs at http://{settings.API_HOST}:{settings.API_PORT}/docs"
        )

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down AI Microservice...")


app = FastAPI(
    title="Assessment AI Service",
    version="1.0.0",
    description="Convert natural language to SQL using Mistral (via Ollama) and execute against SQL Server.",
)


# Include routers
app.include_router(score_analysis_router)
# Root Endpoint
@app.get("/", summary="API Root")
async def root():
    return {
        "service": "Text-to-SQL API",
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
        "ollama_model": settings.OLLAMA_MODEL,
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
