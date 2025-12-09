from fastapi import FastAPI, HTTPException, Response, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, AsyncGenerator
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import Geometry
from shapely import wkb
from shapely.geometry import Point, Polygon, mapping
import geojson
import logging
import os
import json
import uuid
import math
from datetime import datetime
from pathlib import Path
import asyncio
import aiohttp
import random
from .tile_downloader import download_tiles_for_area

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mapping Service",
    description="Geospatial data management and tile serving",
    version="1.0.0"
)

# Database configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgis")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mapping_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "mapuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mappass")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# SQLAlchemy setup
Base = declarative_base()
engine = None
SessionLocal = None

class MapLayer(Base):
    """Map layer model"""
    __tablename__ = "map_layers"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'point', 'polygon', 'heatmap'
    geom = Column(Geometry('GEOMETRY', srid=4326))
    properties = Column(Text)  # JSON string
    style = Column(Text)  # JSON string

@app.on_event("startup")
async def startup_event():
    """Initialize database connection"""
    global engine, SessionLocal
    try:
        logger.info(f"Connecting to database at {POSTGRES_HOST}")
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")

class LayerCreate(BaseModel):
    id: str
    name: str
    type: str
    data: Dict[str, Any]  # GeoJSON
    style: Optional[Dict[str, Any]] = None

class LayerResponse(BaseModel):
    id: str
    name: str
    type: str
    data: Dict[str, Any]

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Mapping Service",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if engine:
            conn = engine.connect()
            conn.close()
            return {"status": "healthy", "database": "connected"}
    except:
        pass
    return {"status": "unhealthy", "database": "disconnected"}

@app.get("/layers")
async def get_layers():
    """Get all map layers"""
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        db = SessionLocal()
        layers = db.query(MapLayer).all()
        
        result = []
        for layer in layers:
            # Convert geometry to GeoJSON
            geom = wkb.loads(bytes(layer.geom.data))
            geojson_data = mapping(geom)
            
            result.append({
                "id": layer.id,
                "name": layer.name,
                "type": layer.type,
                "data": geojson_data,
                "properties": json.loads(layer.properties) if layer.properties else {},
                "style": json.loads(layer.style) if layer.style else {}
            })
        
        db.close()
        return {"layers": result}
    except Exception as e:
        logger.error(f"Error fetching layers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/layers")
async def create_layer(layer: LayerCreate):
    """Create a new map layer"""
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        db = SessionLocal()
        
        # Convert GeoJSON to Shapely geometry
        if layer.data.get("type") == "FeatureCollection":
            # For FeatureCollections, store the first feature's geometry
            # (or we could store multiple rows)
            features = layer.data.get("features", [])
            if features:
                geom_data = features[0]["geometry"]
            else:
                raise ValueError("No features in FeatureCollection")
        elif layer.data.get("type") == "Feature":
            geom_data = layer.data["geometry"]
        else:
            # Assume it's a geometry object directly
            geom_data = layer.data
        
        # Convert coordinates to WKT based on geometry type
        geom_type = geom_data["type"]
        coords = geom_data["coordinates"]
        
        if geom_type == "Point":
            # Point: [lon, lat]
            wkt = f"POINT({coords[0]} {coords[1]})"
        elif geom_type == "Polygon":
            # Polygon: [[lon, lat], ...]
            coords_str = ", ".join([f"{c[0]} {c[1]}" for c in coords[0]])
            wkt = f"POLYGON(({coords_str}))"
        else:
            raise ValueError(f"Unsupported geometry type: {geom_type}")
        
        # Create layer with WKT
        new_layer = MapLayer(
            id=layer.id,
            name=layer.name,
            type=layer.type,
            geom=f"SRID=4326;{wkt}",
            properties=json.dumps(layer.data.get("properties", {})),
            style=json.dumps(layer.style) if layer.style else None
        )
        
        db.add(new_layer)
        db.commit()
        db.close()
        
        logger.info(f"Created layer: {layer.id}")
        return {"message": "Layer created successfully", "id": layer.id}
    except Exception as e:
        logger.error(f"Error creating layer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class LayerUpdate(BaseModel):
    name: Optional[str] = None
    style: Optional[Dict[str, Any]] = None

@app.patch("/layers/{layer_id}")
async def update_layer(layer_id: str, update: LayerUpdate):
    """Update a map layer's name and/or style"""
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        db = SessionLocal()
        layer = db.query(MapLayer).filter(MapLayer.id == layer_id).first()
        
        if not layer:
            raise HTTPException(status_code=404, detail="Layer not found")
        
        # Update name if provided
        if update.name is not None:
            layer.name = update.name
        
        # Update style if provided
        if update.style is not None:
            layer.style = json.dumps(update.style)
        
        db.commit()
        db.close()
        
        logger.info(f"Updated layer: {layer_id}")
        return {"message": "Layer updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating layer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/layers/{layer_id}")
async def delete_layer(layer_id: str):
    """Delete a map layer"""
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        db = SessionLocal()
        layer = db.query(MapLayer).filter(MapLayer.id == layer_id).first()
        
        if not layer:
            raise HTTPException(status_code=404, detail="Layer not found")
        
        db.delete(layer)
        db.commit()
        db.close()
        
        logger.info(f"Deleted layer: {layer_id}")
        return {"message": "Layer deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting layer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tiles/{layer}/{z}/{x}/{y}.png")
async def get_tile(layer: str, z: int, x: int, y: int):
    """Serve map tiles from local cache"""
    tile_path = Path(f"/app/map-tiles/{layer}/{z}/{x}/{y}.png")
    
    if tile_path.exists():
        return FileResponse(tile_path, media_type="image/png")
    else:
        # Return 404 or transparent tile
        raise HTTPException(status_code=404, detail="Tile not found")

class TileDownloadRequest(BaseModel):
    area_name: str
    lat_min: float
    lon_min: float
    lat_max: float
    lon_max: float
    zoom_levels: Optional[List[int]] = None
    layers: Optional[List[str]] = ["osm", "satellite"]

@app.post("/tiles/download")
async def download_tiles(request: TileDownloadRequest, background_tasks: BackgroundTasks):
    """Download tiles for offline use"""
    bounds = {
        "lat_min": request.lat_min,
        "lon_min": request.lon_min,
        "lat_max": request.lat_max,
        "lon_max": request.lon_max
    }
    
    zoom_levels = request.zoom_levels or list(range(12, 17))
    
    # Run download in background
    background_tasks.add_task(
        download_tiles_for_area,
        request.area_name,
        bounds,
        zoom_levels
    )
    
    return {
        "message": "Tile download started",
        "area": request.area_name,
        "bounds": bounds,
        "zoom_levels": zoom_levels
    }

@app.get("/tiles/status")
async def get_tile_status():
    """Get statistics about downloaded tiles"""
    tile_dir = Path("/app/map-tiles")
    stats = {}
    
    for layer in ["osm", "satellite"]:
        layer_path = tile_dir / layer
        if layer_path.exists():
            tile_count = sum(1 for _ in layer_path.rglob("*.png"))
            stats[layer] = {
                "tiles": tile_count,
                "path": str(layer_path)
            }
        else:
            stats[layer] = {"tiles": 0, "path": "not found"}
    
    return stats

# Tile download streaming endpoint
BLOCKED_TILE_SIZE = 7412
MIN_DELAY_BETWEEN_REQUESTS = 1.0
MAX_DELAY_BETWEEN_REQUESTS = 2.0

OSM_SERVERS = [
    "https://a.tile.openstreetmap.org",
    "https://b.tile.openstreetmap.org",
    "https://c.tile.openstreetmap.org"
]
SATELLITE_SERVER = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile"

def lat_lon_to_tile_coords(lat: float, lon: float, zoom: int) -> tuple:
    """Convert latitude/longitude to tile coordinates"""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y

def get_tiles_in_radius(lat: float, lon: float, radius_miles: float, zoom: int) -> list:
    """Get all tile coordinates within a radius"""
    # Convert radius from miles to degrees (approximate)
    radius_lat = radius_miles / 69.0
    radius_lon = radius_miles / (69.0 * math.cos(math.radians(lat)))
    
    # Get bounding box corners
    north = lat + radius_lat
    south = lat - radius_lat
    east = lon + radius_lon
    west = lon - radius_lon
    
    # Get tile coordinates for all four corners
    x_nw, y_nw = lat_lon_to_tile_coords(north, west, zoom)
    x_ne, y_ne = lat_lon_to_tile_coords(north, east, zoom)
    x_sw, y_sw = lat_lon_to_tile_coords(south, west, zoom)
    x_se, y_se = lat_lon_to_tile_coords(south, east, zoom)
    
    # Find the actual min/max tile bounds
    min_x = min(x_nw, x_ne, x_sw, x_se)
    max_x = max(x_nw, x_ne, x_sw, x_se)
    min_y = min(y_nw, y_ne, y_sw, y_se)
    max_y = max(y_nw, y_ne, y_sw, y_se)
    
    # Generate all tiles in the bounding box
    tiles = []
    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            tiles.append((x, y))
    
    logger.info(f"Zoom {zoom}: Calculated {len(tiles)} tiles in radius. Bounds: X[{min_x}-{max_x}], Y[{min_y}-{max_y}]")
    
    return tiles

async def download_single_tile(session: aiohttp.ClientSession, layer: str, zoom: int, x: int, y: int) -> dict:
    """Download a single tile"""
    tile_path = Path(f"/app/map-tiles/{layer}/{zoom}/{x}/{y}.png")
    
    # Check if tile already exists
    if tile_path.exists():
        file_size = tile_path.stat().st_size
        if file_size == BLOCKED_TILE_SIZE:
            return {"status": "blocked", "size": file_size}
        else:
            return {"status": "skipped", "size": file_size}
    
    # Add delay before request
    delay = random.uniform(MIN_DELAY_BETWEEN_REQUESTS, MAX_DELAY_BETWEEN_REQUESTS)
    await asyncio.sleep(delay)
    
    # Build URL
    if layer == "osm":
        server = random.choice(OSM_SERVERS)
        url = f"{server}/{zoom}/{x}/{y}.png"
    elif layer == "satellite":
        url = f"{SATELLITE_SERVER}/{zoom}/{y}/{x}"
    else:
        return {"status": "error", "error": f"Unknown layer: {layer}"}
    
    # Download tile
    headers = {'User-Agent': 'DisasterReliefMappingSystem/1.0 (Training/Testing)'}
    
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status != 200:
                return {"status": "failed", "error": f"HTTP {response.status}"}
            
            content = await response.read()
            content_length = len(content)
            
            # Check if blocked
            if content_length == BLOCKED_TILE_SIZE:
                # Save anyway to mark as blocked
                tile_path.parent.mkdir(parents=True, exist_ok=True)
                with open(tile_path, 'wb') as f:
                    f.write(content)
                return {"status": "blocked", "size": content_length}
            
            # Save tile
            tile_path.parent.mkdir(parents=True, exist_ok=True)
            with open(tile_path, 'wb') as f:
                f.write(content)
            
            return {"status": "success", "size": content_length}
            
    except asyncio.TimeoutError:
        return {"status": "timeout"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def stream_tile_download(lat: float, lon: float, radius_miles: float, min_zoom: int, max_zoom: int, layers: list) -> AsyncGenerator:
    """Stream tile download progress as SSE events"""
    
    async with aiohttp.ClientSession() as session:
        for layer in layers:
            for zoom in range(min_zoom, max_zoom + 1):
                # Get tiles for this zoom level
                tiles = get_tiles_in_radius(lat, lon, radius_miles, zoom)
                total_tiles = len(tiles)
                
                stats = {
                    "success": 0,
                    "skipped": 0,
                    "blocked": 0,
                    "failed": 0,
                    "timeout": 0,
                    "error": 0
                }
                
                # Download tiles sequentially
                for idx, (x, y) in enumerate(tiles):
                    result = await download_single_tile(session, layer, zoom, x, y)
                    stats[result["status"]] += 1
                    
                    # Send progress event
                    event_data = {
                        "type": "progress",
                        "layer": layer,
                        "zoom": zoom,
                        "tile_x": x,
                        "tile_y": y,
                        "status": result["status"],
                        "size": result.get("size"),
                        "completed": idx + 1,
                        "total_tiles": total_tiles,
                        **stats
                    }
                    
                    yield f"data: {json.dumps(event_data)}\n\n"
                
                # Send layer complete event
                yield f"data: {json.dumps({'type': 'layer_complete', 'layer': layer, 'zoom': zoom, **stats})}\n\n"
        
        # Send completion event
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"

@app.get("/tiles/download")
async def download_tiles_stream(
    lat: float,
    lon: float,
    radius_miles: float = 5.0,
    min_zoom: int = 13,
    max_zoom: int = 19,
    layers: str = "osm,satellite"
):
    """
    Stream tile download progress (Server-Sent Events)
    
    Args:
        lat: Center latitude
        lon: Center longitude
        radius_miles: Radius in miles (default 5)
        min_zoom: Minimum zoom level (default 13)
        max_zoom: Maximum zoom level (default 19)
        layers: Comma-separated list of layers (default "osm,satellite")
    """
    layer_list = layers.split(',')
    
    return StreamingResponse(
        stream_tile_download(lat, lon, radius_miles, min_zoom, max_zoom, layer_list),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

# Shape generation helpers
def generate_circle_coordinates(center_lat: float, center_lon: float, radius_miles: float, num_points: int = 32) -> List[List[float]]:
    """
    Generate coordinates for a circle around a center point.
    
    Args:
        center_lat: Center latitude in degrees
        center_lon: Center longitude in degrees
        radius_miles: Radius in miles
        num_points: Number of points to generate (more = smoother circle)
    
    Returns:
        List of [lon, lat] coordinate pairs forming a closed polygon
    """
    # Convert miles to degrees (approximate at UK latitudes ~51°N)
    # 1 degree latitude ≈ 69 miles
    # 1 degree longitude ≈ 69 * cos(latitude) miles
    radius_lat = radius_miles / 69.0
    radius_lon = radius_miles / (69.0 * math.cos(math.radians(center_lat)))
    
    coordinates = []
    for i in range(num_points):
        angle = (i * 360.0 / num_points) * (math.pi / 180.0)  # Convert to radians
        lat = center_lat + radius_lat * math.cos(angle)
        lon = center_lon + radius_lon * math.sin(angle)
        coordinates.append([lon, lat])
    
    # Close the polygon (first point = last point)
    coordinates.append(coordinates[0])
    
    return coordinates


def generate_rectangle_coordinates(center_lat: float, center_lon: float, width_miles: float, height_miles: float) -> List[List[float]]:
    """
    Generate coordinates for a rectangle centered on a point.
    
    Args:
        center_lat: Center latitude in degrees
        center_lon: Center longitude in degrees
        width_miles: Width in miles (east-west)
        height_miles: Height in miles (north-south)
    
    Returns:
        List of [lon, lat] coordinate pairs forming a closed rectangle
    """
    # Convert miles to degrees
    half_height_deg = (height_miles / 2.0) / 69.0
    half_width_deg = (width_miles / 2.0) / (69.0 * math.cos(math.radians(center_lat)))
    
    # Generate rectangle corners (clockwise from top-left)
    coordinates = [
        [center_lon - half_width_deg, center_lat + half_height_deg],  # Top-left
        [center_lon + half_width_deg, center_lat + half_height_deg],  # Top-right
        [center_lon + half_width_deg, center_lat - half_height_deg],  # Bottom-right
        [center_lon - half_width_deg, center_lat - half_height_deg],  # Bottom-left
        [center_lon - half_width_deg, center_lat + half_height_deg],  # Close polygon
    ]
    
    return coordinates


def generate_ellipse_coordinates(center_lat: float, center_lon: float, width_miles: float, height_miles: float, num_points: int = 32) -> List[List[float]]:
    """
    Generate coordinates for an ellipse centered on a point.
    
    Args:
        center_lat: Center latitude in degrees
        center_lon: Center longitude in degrees
        width_miles: Width in miles (east-west diameter)
        height_miles: Height in miles (north-south diameter)
        num_points: Number of points to generate
    
    Returns:
        List of [lon, lat] coordinate pairs forming a closed ellipse
    """
    # Convert miles to degrees (semi-major and semi-minor axes)
    radius_lat = (height_miles / 2.0) / 69.0
    radius_lon = (width_miles / 2.0) / (69.0 * math.cos(math.radians(center_lat)))
    
    coordinates = []
    for i in range(num_points):
        angle = (i * 360.0 / num_points) * (math.pi / 180.0)
        lat = center_lat + radius_lat * math.cos(angle)
        lon = center_lon + radius_lon * math.sin(angle)
        coordinates.append([lon, lat])
    
    # Close the polygon
    coordinates.append(coordinates[0])
    
    return coordinates


class DrawShapeRequest(BaseModel):
    shape_type: str  # "circle", "rectangle", "ellipse"
    center_lat: float
    center_lon: float
    radius_miles: Optional[float] = None  # For circles
    width_miles: Optional[float] = None  # For rectangles and ellipses
    height_miles: Optional[float] = None  # For rectangles and ellipses
    num_points: Optional[int] = 32  # Smoothness for circles/ellipses
    style: Optional[Dict[str, Any]] = None
    label: Optional[str] = None


@app.post("/draw_shape")
async def draw_shape(request: DrawShapeRequest):
    """
    Generate and draw a shape on the map.
    
    This endpoint handles the coordinate generation server-side, so the LLM
    just needs to specify the shape type and parameters.
    """
    try:
        # Generate coordinates based on shape type
        if request.shape_type == "circle":
            if request.radius_miles is None:
                raise HTTPException(status_code=400, detail="radius_miles required for circle")
            coordinates = generate_circle_coordinates(
                request.center_lat,
                request.center_lon,
                request.radius_miles,
                request.num_points or 32
            )
        
        elif request.shape_type == "rectangle":
            if request.width_miles is None or request.height_miles is None:
                raise HTTPException(status_code=400, detail="width_miles and height_miles required for rectangle")
            coordinates = generate_rectangle_coordinates(
                request.center_lat,
                request.center_lon,
                request.width_miles,
                request.height_miles
            )
        
        elif request.shape_type == "ellipse":
            if request.width_miles is None or request.height_miles is None:
                raise HTTPException(status_code=400, detail="width_miles and height_miles required for ellipse")
            coordinates = generate_ellipse_coordinates(
                request.center_lat,
                request.center_lon,
                request.width_miles,
                request.height_miles,
                request.num_points or 32
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown shape_type: {request.shape_type}")
        
        # Generate unique layer ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        milliseconds = int(datetime.now().microsecond / 1000)
        layer_id = f"polygon_{timestamp}_{milliseconds}"
        
        # Create GeoJSON with the generated coordinates
        geojson_data = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coordinates]
                },
                "properties": {
                    "layer_id": layer_id,
                    "shape_type": request.shape_type,
                    "label": request.label or f"{request.shape_type.capitalize()} ({request.radius_miles or request.width_miles} miles)",
                    **(request.style or {})
                }
            }]
        }
        
        return {
            "layer_id": layer_id,
            "geojson": geojson_data,
            "message": f"{request.shape_type.capitalize()} drawn successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error drawing shape: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/execute")
async def execute_function(function_call: Dict[str, Any]):
    """Execute map-related function calls from LLM"""
    function_name = function_call.get("name")
    parameters = function_call.get("parameters", {})
    
    if function_name == "map_plot_points":
        # Create point layer
        points = parameters.get("points", [])
        layer_name = parameters.get("layer_name")
        
        # Generate unique layer ID if not provided
        if not layer_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            layer_name = f"points_{timestamp}"
        else:
            # Make the provided name unique by appending timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            layer_name = f"{layer_name}_{timestamp}"
        
        # Convert to GeoJSON
        features = []
        for point in points:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [point["lon"], point["lat"]]
                },
                "properties": {
                    "label": point.get("label", ""),
                    "marker_type": point.get("marker_type", "default"),
                    **point.get("properties", {})
                }
            })
        
        geojson_data = {
            "type": "FeatureCollection",
            "features": features
        }
        
        layer = LayerCreate(
            id=layer_name,
            name=layer_name,
            type="point",
            data=geojson_data
        )
        
        return await create_layer(layer)
    
    elif function_name == "map_draw_polygon":
        # Create polygon layer
        coordinates = parameters.get("coordinates", [])
        style = parameters.get("style", {})
        
        # Auto-close polygon if not closed (first and last coords must match)
        if coordinates and len(coordinates) > 0:
            first_coord = coordinates[0]
            last_coord = coordinates[-1]
            # Check if polygon is closed (first == last)
            if first_coord != last_coord:
                # Auto-close by appending first coordinate
                coordinates.append(first_coord)
                logger.info(f"Auto-closed polygon: added {first_coord} to close the ring")
        
        # Generate unique layer ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        layer_id = f"polygon_{timestamp}"
        
        geojson_data = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [coordinates]
            },
            "properties": {}
        }
        
        layer = LayerCreate(
            id=layer_id,
            name=f"Polygon {timestamp}",
            type="polygon",
            data=geojson_data,
            style=style
        )
        
        return await create_layer(layer)
    
    elif function_name == "map_draw_shape":
        # Draw a geometric shape (circle, rectangle, or ellipse)
        shape_type = parameters.get("shape_type")
        center_lat = parameters.get("center_lat")
        center_lon = parameters.get("center_lon")
        
        if not all([shape_type, center_lat, center_lon]):
            raise HTTPException(status_code=400, detail="shape_type, center_lat, and center_lon are required")
        
        # Create DrawShapeRequest
        request_data = DrawShapeRequest(
            shape_type=shape_type,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_miles=parameters.get("radius_miles"),
            width_miles=parameters.get("width_miles"),
            height_miles=parameters.get("height_miles"),
            style=parameters.get("style", {}),
            label=parameters.get("label")
        )
        
        # Generate coordinates based on shape type
        if request_data.shape_type == "circle":
            if request_data.radius_miles is None:
                raise HTTPException(status_code=400, detail="radius_miles is required for circles")
            coordinates = generate_circle_coordinates(
                request_data.center_lat, 
                request_data.center_lon, 
                request_data.radius_miles
            )
        elif request_data.shape_type == "rectangle":
            if request_data.width_miles is None or request_data.height_miles is None:
                raise HTTPException(status_code=400, detail="width_miles and height_miles are required for rectangles")
            coordinates = generate_rectangle_coordinates(
                request_data.center_lat,
                request_data.center_lon,
                request_data.width_miles,
                request_data.height_miles
            )
        elif request_data.shape_type == "ellipse":
            if request_data.width_miles is None or request_data.height_miles is None:
                raise HTTPException(status_code=400, detail="width_miles and height_miles are required for ellipses")
            coordinates = generate_ellipse_coordinates(
                request_data.center_lat,
                request_data.center_lon,
                request_data.width_miles,
                request_data.height_miles
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown shape type: {request_data.shape_type}")
        
        # Generate unique layer ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        layer_id = f"{request_data.shape_type}_{timestamp}"
        
        # Create GeoJSON
        geojson_data = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [coordinates]
            },
            "properties": {
                "label": request_data.label or f"{request_data.shape_type.capitalize()}"
            }
        }
        
        # Create layer
        layer = LayerCreate(
            id=layer_id,
            name=request_data.label or f"{request_data.shape_type.capitalize()} {timestamp}",
            type="polygon",
            data=geojson_data,
            style=request_data.style
        )
        
        result = await create_layer(layer)
        
        return {
            "layer_id": layer_id,
            "geojson": geojson_data,
            "message": f"{request_data.shape_type.capitalize()} drawn successfully"
        }
    
    elif function_name == "map_delete_layer":
        # Delete a layer
        layer_id = parameters.get("layer_id")
        if not layer_id:
            raise HTTPException(status_code=400, detail="layer_id is required")
        
        return await delete_layer(layer_id)
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown function: {function_name}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
