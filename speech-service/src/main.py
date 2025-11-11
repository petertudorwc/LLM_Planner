from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import whisper
import logging
import os
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Speech Recognition Service",
    description="Whisper-based speech-to-text service",
    version="1.0.0"
)

MODEL_SIZE = os.getenv("MODEL_SIZE", "base")
CACHE_DIR = os.getenv("CACHE_DIR", "/models")

# Global model instance
model = None

@app.on_event("startup")
async def startup_event():
    """Load Whisper model on startup"""
    global model
    logger.info(f"Loading Whisper model: {MODEL_SIZE}")
    try:
        model = whisper.load_model(MODEL_SIZE, download_root=CACHE_DIR)
        logger.info("Whisper model loaded successfully")
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise

class TranscriptionResponse(BaseModel):
    text: str
    language: str
    confidence: float = 0.0

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Speech Recognition Service",
        "model": MODEL_SIZE,
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "healthy", "model": MODEL_SIZE}

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe audio file to text"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await audio.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Transcribe
        logger.info(f"Transcribing audio file: {audio.filename}")
        result = model.transcribe(temp_path, fp16=False)
        
        # Clean up temp file
        os.unlink(temp_path)
        
        logger.info(f"Transcription complete: {result['text'][:50]}...")
        
        return {
            "text": result["text"],
            "language": result.get("language", "en"),
            "confidence": 0.9  # Whisper doesn't provide confidence scores
        }
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        if 'temp_path' in locals():
            try:
                os.unlink(temp_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_models():
    """List available Whisper models"""
    return {
        "available_models": ["tiny", "base", "small", "medium", "large"],
        "current_model": MODEL_SIZE
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
