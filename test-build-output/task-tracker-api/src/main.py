import os
import logging
import sys
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from .database import init_db, check_database_connection
from .routes import tasks_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log', mode='a')
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Task Tracker API...")
    
    if not check_database_connection():
        logger.error("Failed to connect to database")
        raise RuntimeError("Database connection failed")
    
    init_db()
    logger.info("Database initialized successfully")
    
    yield
    
    logger.info("Shutting down Task Tracker API...")


app = FastAPI(
    title="Task Tracker API",
    description="""
## Task Tracker API

A RESTful API for managing tasks with authentication and rate limiting.

### Features
- **Full CRUD operations** for task management
- **API Key authentication** with rate limiting
- **Pagination support** for listing tasks
- **Status filtering** for task queries
- **Comprehensive error handling**
- **Database health monitoring**

### Authentication
All task endpoints require API key authentication. Provide your API key in one of these ways:
- Header: `X-API-Key: your-api-key`
- Query parameter: `?api_key=your-api-key`

### Rate Limiting
API requests are rate-limited to prevent abuse. Default limits apply per API key.
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "Task Tracker Support",
        "email": "support@tasktracker.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
)

origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database error on {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database operation failed",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.error(f"Value error on {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": str(exc),
            "status_code": status.HTTP_400_BAD_REQUEST,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error on {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.get(
    "/",
    summary="API Root",
    description="Get basic information about the Task Tracker API",
    tags=["general"]
)
async def root():
    """Welcome endpoint with API information."""
    return {
        "message": "Welcome to Task Tracker API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get(
    "/health",
    summary="Health Check",
    description="Check the health status of the API and its dependencies",
    tags=["general"],
    response_description="Health status including database connectivity"
)
async def health_check():
    """Check API and database health status."""
    db_status = "healthy" if check_database_connection() else "unhealthy"
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status
    }


# Include task routes
app.include_router(tasks_router)