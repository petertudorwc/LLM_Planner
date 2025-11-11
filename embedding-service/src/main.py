from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from sentence_transformers import SentenceTransformer
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Embedding Service",
    description="Text embedding service using sentence-transformers",
    version="1.0.0"
)

# Model configuration
MODEL_NAME = os.getenv("MODEL_NAME", "sentence-transformers/all-mpnet-base-v2")
CACHE_DIR = os.getenv("CACHE_DIR", "/models")

# Global model instance
model = None

@app.on_event("startup")
async def startup_event():
    """Load model on startup"""
    global model
    logger.info(f"Loading embedding model: {MODEL_NAME}")
    try:
        model = SentenceTransformer(MODEL_NAME, cache_folder=CACHE_DIR)
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise

class EmbedRequest(BaseModel):
    texts: List[str]
    normalize: bool = True

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dimension: int

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Embedding Service",
        "model": MODEL_NAME,
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "dimension": model.get_sentence_embedding_dimension()
    }

@app.post("/embed", response_model=EmbedResponse)
async def embed_texts(request: EmbedRequest):
    """Generate embeddings for input texts"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Generate embeddings
        embeddings = model.encode(
            request.texts,
            normalize_embeddings=request.normalize,
            convert_to_numpy=True
        )
        
        # Convert to list format
        embeddings_list = embeddings.tolist()
        
        logger.info(f"Generated embeddings for {len(request.texts)} texts")
        
        return {
            "embeddings": embeddings_list,
            "model": MODEL_NAME,
            "dimension": len(embeddings_list[0]) if embeddings_list else 0
        }
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/similarity")
async def compute_similarity(texts1: List[str], texts2: List[str]):
    """Compute cosine similarity between two sets of texts"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        from sentence_transformers import util
        
        # Generate embeddings
        embeddings1 = model.encode(texts1, convert_to_tensor=True)
        embeddings2 = model.encode(texts2, convert_to_tensor=True)
        
        # Compute cosine similarity
        similarities = util.cos_sim(embeddings1, embeddings2)
        
        return {
            "similarities": similarities.tolist(),
            "shape": list(similarities.shape)
        }
    except Exception as e:
        logger.error(f"Error computing similarity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
