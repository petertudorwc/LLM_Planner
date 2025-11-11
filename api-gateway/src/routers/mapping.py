from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import httpx
import logging

from ..core.security import get_current_user
from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

class MapLayer(BaseModel):
    id: str
    name: str
    type: str  # 'point', 'polygon', 'heatmap', etc.
    data: dict  # GeoJSON
    style: Optional[dict] = None

class LayerUpdate(BaseModel):
    name: Optional[str] = None
    style: Optional[dict] = None

class MapBounds(BaseModel):
    north: float
    south: float
    east: float
    west: float

@router.get("/layers")
async def get_layers(current_user: dict = Depends(get_current_user)):
    """Get all map layers"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.MAPPING_SERVICE_URL}/layers",
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Mapping service error")
            
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching map layers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/layers")
async def create_layer(
    layer: MapLayer,
    current_user: dict = Depends(get_current_user)
):
    """Create a new map layer"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.MAPPING_SERVICE_URL}/layers",
                json=layer.dict(),
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Mapping service error")
            
            logger.info(f"User {current_user['username']} created layer {layer.id}")
            return response.json()
    except Exception as e:
        logger.error(f"Error creating map layer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/layers/{layer_id}")
async def update_layer(
    layer_id: str,
    update: LayerUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a map layer's name and/or style"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{settings.MAPPING_SERVICE_URL}/layers/{layer_id}",
                json=update.dict(exclude_none=True),
                timeout=30.0
            )
            
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Layer not found")
            elif response.status_code != 200:
                raise HTTPException(status_code=500, detail="Mapping service error")
            
            logger.info(f"User {current_user['username']} updated layer {layer_id}")
            return response.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating map layer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/layers/{layer_id}")
async def delete_layer(
    layer_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a map layer"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{settings.MAPPING_SERVICE_URL}/layers/{layer_id}",
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Mapping service error")
            
            logger.info(f"User {current_user['username']} deleted layer {layer_id}")
            return {"message": "Layer deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting map layer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tiles/{z}/{x}/{y}.png")
async def get_tile(z: int, x: int, y: int, layer: str = "osm"):
    """Get map tile (proxy to tile service)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.MAPPING_SERVICE_URL}/tiles/{layer}/{z}/{x}/{y}.png",
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail="Tile not found")
            
            return response.content
    except Exception as e:
        logger.error(f"Error fetching tile: {e}")
        raise HTTPException(status_code=500, detail=str(e))
