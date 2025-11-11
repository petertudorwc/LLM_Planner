from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import httpx
import logging
import os
from pathlib import Path
import json

from .processors import pdf_processor, docx_processor, excel_processor, csv_processor, geospatial_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Data Ingestion Service",
    description="Process and ingest documents into vector store",
    version="1.0.0"
)

# Service URLs
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://embedding-service:8002")
VECTOR_STORE_URL = os.getenv("VECTOR_STORE_URL", "http://vector-store:6333")
MAPPING_SERVICE_URL = os.getenv("MAPPING_SERVICE_URL", "http://mapping-service:8003")

class FileInfo(BaseModel):
    filename: str
    path: str
    size: int

class ProcessRequest(BaseModel):
    files: List[FileInfo]

class ProcessResponse(BaseModel):
    status: str
    processed_files: int
    chunks_created: int
    errors: List[str] = []

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Data Ingestion Service",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/process", response_model=ProcessResponse)
async def process_files(request: ProcessRequest):
    """Process uploaded files and ingest into vector store"""
    processed_count = 0
    total_chunks = 0
    errors = []
    
    for file_info in request.files:
        try:
            file_path = Path(file_info.path)
            extension = file_path.suffix.lower()
            
            logger.info(f"Processing file: {file_info.filename}")
            
            # Extract text based on file type
            if extension == ".pdf":
                text_chunks = pdf_processor.process(file_path)
            elif extension in [".docx", ".doc"]:
                text_chunks = docx_processor.process(file_path)
            elif extension in [".xlsx", ".xls"]:
                text_chunks = excel_processor.process(file_path)
            elif extension == ".csv":
                text_chunks = csv_processor.process(file_path)
            elif extension in [".geojson", ".shp", ".kml"]:
                # Handle geospatial files differently
                result = await geospatial_processor.process(file_path, MAPPING_SERVICE_URL)
                processed_count += 1
                continue
            else:
                errors.append(f"Unsupported file type: {extension}")
                continue
            
            # Generate embeddings
            async with httpx.AsyncClient() as client:
                embed_response = await client.post(
                    f"{EMBEDDING_SERVICE_URL}/embed",
                    json={"texts": text_chunks},
                    timeout=60.0
                )
                
                if embed_response.status_code != 200:
                    errors.append(f"Error generating embeddings for {file_info.filename}")
                    continue
                
                embeddings = embed_response.json()["embeddings"]
            
            # Store in vector database
            points = []
            for i, (chunk, embedding) in enumerate(zip(text_chunks, embeddings)):
                points.append({
                    "id": f"{file_info.filename}_{i}",
                    "vector": embedding,
                    "payload": {
                        "text": chunk,
                        "filename": file_info.filename,
                        "chunk_index": i
                    }
                })
            
            async with httpx.AsyncClient() as client:
                # Create collection if not exists
                try:
                    await client.put(
                        f"{VECTOR_STORE_URL}/collections/documents",
                        json={
                            "vectors": {
                                "size": len(embeddings[0]),
                                "distance": "Cosine"
                            }
                        },
                        timeout=30.0
                    )
                except:
                    pass  # Collection might already exist
                
                # Insert points
                insert_response = await client.put(
                    f"{VECTOR_STORE_URL}/collections/documents/points",
                    json={"points": points},
                    timeout=60.0
                )
                
                if insert_response.status_code not in [200, 201]:
                    errors.append(f"Error storing vectors for {file_info.filename}")
                    continue
            
            processed_count += 1
            total_chunks += len(text_chunks)
            logger.info(f"Successfully processed {file_info.filename}: {len(text_chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error processing {file_info.filename}: {e}")
            errors.append(f"{file_info.filename}: {str(e)}")
    
    return {
        "status": "completed" if not errors else "completed_with_errors",
        "processed_files": processed_count,
        "chunks_created": total_chunks,
        "errors": errors
    }

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get processing status (placeholder for async processing)"""
    # TODO: Implement async job tracking
    return {"job_id": job_id, "status": "completed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
