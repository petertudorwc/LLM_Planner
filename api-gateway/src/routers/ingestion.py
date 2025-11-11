from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List
import httpx
import logging
import aiofiles
import os

from ..core.security import get_current_user
from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = "/app/uploads"

@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload files for ingestion"""
    uploaded_files = []
    
    try:
        for file in files:
            # Save file
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            uploaded_files.append({
                "filename": file.filename,
                "path": file_path,
                "size": len(content)
            })
        
        # Send to ingestion service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.INGESTION_SERVICE_URL}/process",
                json={"files": uploaded_files},
                timeout=300.0  # 5 minutes for large files
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Ingestion service error")
            
            result = response.json()
        
        logger.info(f"User {current_user['username']} uploaded {len(files)} files")
        
        return {
            "message": f"Successfully uploaded and processed {len(files)} files",
            "files": uploaded_files,
            "processing_result": result
        }
        
    except Exception as e:
        logger.error(f"Error uploading files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}")
async def get_ingestion_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get status of ingestion job"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.INGESTION_SERVICE_URL}/status/{job_id}",
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail="Job not found")
            
            return response.json()
    except Exception as e:
        logger.error(f"Error checking ingestion status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents")
async def list_documents(current_user: dict = Depends(get_current_user)):
    """List all ingested documents"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.VECTOR_STORE_URL}/collections/documents/points/scroll",
                params={"limit": 100},
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Vector store error")
            
            return response.json()
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
