import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import your controllers
from controller.session_api_controller import router as session_router
from controller.requirements_controller import router as requirements_router
from controller.test_cases_controller import router as test_cases_router

# Import database manager
from modules.database.database_manager import db_manager
from modules.cache.redis_manager import redis_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Test Case Generator API",
    description="AI-powered test case generation with RAG and session management",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# GLOBAL ERROR HANDLERS
# ===============================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP error {exc.status_code} at {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "path": str(request.url),
            "method": request.method
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error at {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "path": str(request.url),
            "method": request.method
        }
    )

# ===============================
# STARTUP AND SHUTDOWN EVENTS
# ===============================

@app.on_event("startup")
async def startup():
    try:
        await db_manager.initialize()
        await redis_manager.initialize()
        logger.info("✅ Database initialized successfully")
        logger.info("✅ Application started successfully")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown():
    try:
        await db_manager.close()
        logger.info("✅ Database connections closed")
        logger.info("✅ Application shutdown complete")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")

# ===============================
# ROUTE REGISTRATION
# ===============================

# Register all routers with proper prefixes
app.include_router(
    session_router,
    prefix="/api/v2/sessions",
    tags=["Session Management"]
)

app.include_router(
    requirements_router,
    prefix="/api/v2/requirements",
    tags=["Requirements Analysis"]
)

app.include_router(
    test_cases_router,
    prefix="/api/v2/test-cases",
    tags=["Test Case Generation"]
)

# ===============================
# ROOT ENDPOINTS
# ===============================

@app.get("/")
async def root():
    return {
        "message": "Test Case Generator API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    try:
        # Check database connection
        async with db_manager.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

        return {
            "status": "healthy",
            "database": "connected",
            "agents": "ready",
            "timestamp": "2025-09-17T00:20:00Z"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )

@app.get("/api/info")
async def api_info():
    return {
        "api_name": "Test Case Generator",
        "version": "2.0.0",
        "endpoints": {
            "sessions": "/api/v2/sessions",
            "requirements": "/api/v2/requirements",
            "test_cases": "/api/v2/test-cases"
        },
        "features": [
            "Session Management",
            "Requirements Analysis",
            "Test Case Generation",
            "RAG Integration",
            "Coverage Reports",
            "Analytics"
        ]
    }

# ===============================
# MAIN ENTRY POINT
# ===============================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
