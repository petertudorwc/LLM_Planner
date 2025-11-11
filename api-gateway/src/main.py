from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import logging

from .routers import auth, chat, mapping, ingestion, speech
from .core.config import settings
from .core.websocket_manager import websocket_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 Starting LLM Planner API Gateway")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    yield
    logger.info("👋 Shutting down LLM Planner API Gateway")

# Create FastAPI app
app = FastAPI(
    title="LLM Planner API Gateway",
    description="Central orchestrator for AI-powered disaster relief planning system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(mapping.router, prefix="/api/mapping", tags=["Mapping"])
app.include_router(ingestion.router, prefix="/api/ingest", tags=["Data Ingestion"])
app.include_router(speech.router, prefix="/api/speech", tags=["Speech"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "LLM Planner API Gateway",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "services": {
            "api_gateway": "up",
            "llm_service": settings.LLM_SERVICE_URL,
            "vector_store": settings.VECTOR_STORE_URL,
            "embedding_service": settings.EMBEDDING_SERVICE_URL,
            "mapping_service": settings.MAPPING_SERVICE_URL,
            "speech_service": settings.SPEECH_SERVICE_URL,
            "ingestion_service": settings.INGESTION_SERVICE_URL
        }
    }

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time communication"""
    await websocket_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            # Handle different message types
            if data.get("type") == "chat":
                # Process chat message and broadcast response
                await websocket_manager.send_personal_message(
                    {"type": "chat_response", "message": "Processing..."},
                    client_id
                )
            elif data.get("type") == "map_update":
                # Broadcast map updates to all connected clients
                await websocket_manager.broadcast(data)
    except WebSocketDisconnect:
        websocket_manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
