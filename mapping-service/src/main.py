from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
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
from datetime import datetime

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
    """Serve map tiles"""
    tile_path = f"/app/map-tiles/{layer}/{z}/{x}/{y}.png"
    
    if os.path.exists(tile_path):
        return FileResponse(tile_path, media_type="image/png")
    else:
        # Return 404 or transparent tile
        raise HTTPException(status_code=404, detail="Tile not found")

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
