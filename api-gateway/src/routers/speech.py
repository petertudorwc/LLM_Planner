from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
import httpx
import logging
import aiofiles
import os

from ..core.security import get_current_user
from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Transcribe audio file to text"""
    try:
        # Read audio file
        audio_content = await audio.read()
        
        # Send to speech service
        async with httpx.AsyncClient() as client:
            files = {"audio": (audio.filename, audio_content, audio.content_type)}
            response = await client.post(
                f"{settings.SPEECH_SERVICE_URL}/transcribe",
                files=files,
                timeout=60.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Speech service error")
            
            result = response.json()
        
        logger.info(f"User {current_user['username']} transcribed audio")
        
        return {
            "text": result.get("text", ""),
            "language": result.get("language", "en"),
            "confidence": result.get("confidence", 0.0)
        }
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def list_speech_models(current_user: dict = Depends(get_current_user)):
    """List available speech recognition models"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SPEECH_SERVICE_URL}/models",
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Speech service error")
            
            return response.json()
    except Exception as e:
        logger.error(f"Error listing speech models: {e}")
        raise HTTPException(status_code=500, detail=str(e))
