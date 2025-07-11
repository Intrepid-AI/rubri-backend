import os

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logger import get_logger
from app.api.v1.routes import router as api_v1_router
from app.api.v1.datamodels import ValidationErrorResponse, ErrorResponse
from app.db_ops.database import init_db
from app.constants import Constants
from app.websocket_manager import connection_manager


# Initialize logger
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=Constants.APP_NAME.value,
    description="API for generating and managing evaluation rubrics based on job descriptions and candidate resumes",
    version=Constants.APP_VERSION.value,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        logger.error("Application may not function correctly without a database")

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "status_code": 422},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status_code": 500},
    )

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Rubri-Backend API",
        "docs": "/docs",
        "redoc": "/redoc",
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.websocket("/ws/progress/{task_id}")
async def websocket_progress_endpoint(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time task progress updates
    
    Connect to this endpoint to receive real-time progress updates for a specific task.
    The task_id should be the ID returned when starting an async task.
    """
    await connection_manager.connect(websocket, task_id)
    
    try:
        while True:
            # Keep the connection alive and listen for client messages
            data = await websocket.receive_text()
            
            # Handle client messages (e.g., ping/pong)
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, task_id)
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
        connection_manager.disconnect(websocket, task_id)

if __name__ == "__main__":
    
    port = Constants.APP_PORT.value
    host = Constants.APP_HOST.value
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=Constants.APP_DEBUG.value,
        log_level="info",
    )