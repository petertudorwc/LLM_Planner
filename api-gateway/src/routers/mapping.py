from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
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

@router.get("/tiles/{layer}/{z}/{x}/{y}.png")
async def get_tile(layer: str, z: int, x: int, y: int):
    """Get map tile (proxy to tile service)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.MAPPING_SERVICE_URL}/tiles/{layer}/{z}/{x}/{y}.png",
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail="Tile not found")
            
            # Return as PNG image with proper content type
            return Response(content=response.content, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching tile {layer}/{z}/{x}/{y}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tiles/status")
async def get_tile_status(current_user: dict = Depends(get_current_user)):
    """Get tile cache status"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.MAPPING_SERVICE_URL}/tiles/status",
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Mapping service error")
            
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching tile status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tiles/download")
async def download_tiles(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Start tile download in background"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.MAPPING_SERVICE_URL}/tiles/download",
                json=request,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Mapping service error")
            
            logger.info(f"User {current_user['username']} started tile download: {request.get('area_name')}")
            return response.json()
    except Exception as e:
        logger.error(f"Error starting tile download: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tiles/download")
async def download_tiles_stream(
    lat: float,
    lon: float,
    radius_miles: float = 5.0,
    min_zoom: int = 13,
    max_zoom: int = 19,
    layers: str = "osm,satellite",
    current_user: dict = Depends(get_current_user)
):
    """Stream tile download progress (Server-Sent Events)"""
    try:
        # Build URL with query parameters
        url = f"{settings.MAPPING_SERVICE_URL}/tiles/download"
        params = {
            "lat": lat,
            "lon": lon,
            "radius_miles": radius_miles,
            "min_zoom": min_zoom,
            "max_zoom": max_zoom,
            "layers": layers
        }
        
        logger.info(f"User {current_user['username']} streaming tile download: lat={lat}, lon={lon}, radius={radius_miles}mi, url={url}")
        
        # Stream the response from mapping service
        async def stream_from_mapping_service():
            try:
                # Use a very long timeout for streaming
                timeout = httpx.Timeout(connect=10.0, read=None, write=None, pool=None)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream("GET", url, params=params) as response:
                        logger.info(f"Mapping service response status: {response.status_code}")
                        
                        if response.status_code != 200:
                            error_text = await response.aread()
                            logger.error(f"Mapping service error: {response.status_code} - {error_text}")
                            yield f"data: {{'type': 'error', 'message': 'Mapping service error: {response.status_code}'}}\n\n".encode()
                            return
                        
                        async for chunk in response.aiter_bytes():
                            yield chunk
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: {{'type': 'error', 'message': 'Stream error: {str(e)}'}}\n\n".encode()
        
        return StreamingResponse(
            stream_from_mapping_service(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        logger.error(f"Error streaming tile download: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/draw_shape")
async def draw_shape(request: dict):
    """Draw a shape on the map (circle, rectangle, ellipse)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.MAPPING_SERVICE_URL}/draw_shape",
                json=request,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            return response.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error drawing shape: {e}")
        raise HTTPException(status_code=500, detail=str(e))
