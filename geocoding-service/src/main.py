"""
Geocoding Service - GeoNames lookup and reverse geocoding
"""
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Geocoding Service",
    description="GeoNames-based geocoding and place name lookup",
    version="1.0.0"
)

# Database configuration
DB_HOST = os.getenv("POSTGRES_HOST", "postgis")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "mapping_db")
DB_USER = os.getenv("POSTGRES_USER", "mapuser")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mappass123")

class Place(BaseModel):
    geonameid: int
    name: str
    latitude: float
    longitude: float
    feature_class: str
    feature_code: str
    population: int
    admin1: Optional[str] = None
    admin2: Optional[str] = None

class GeocodeResponse(BaseModel):
    places: List[Place]
    count: int

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Geocoding Service",
        "description": "GeoNames UK place lookup",
        "endpoints": {
            "/search": "Search for places by name",
            "/nearby": "Find places near coordinates",
            "/reverse": "Reverse geocode coordinates to place name"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM geonames")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "geonames_count": result['count']
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.get("/search", response_model=GeocodeResponse)
async def search_place(
    q: str = Query(..., description="Place name to search for"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results to return"),
    feature_class: Optional[str] = Query(None, description="Filter by feature class (P=populated place, A=admin)")
):
    """
    Search for places by name
    
    Feature classes:
    - P: Populated places (cities, towns, villages)
    - A: Administrative areas (counties, regions)
    - H: Water features (rivers, lakes)
    - T: Terrain features (hills, mountains)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query
        query = """
            SELECT 
                geonameid, name, latitude, longitude, 
                feature_class, feature_code, population,
                admin1_code as admin1, admin2_code as admin2
            FROM geonames
            WHERE 
                (name ILIKE %s OR asciiname ILIKE %s OR alternatenames ILIKE %s)
        """
        params = [f"%{q}%", f"%{q}%", f"%{q}%"]
        
        if feature_class:
            query += " AND feature_class = %s"
            params.append(feature_class)
        
        # Order by: exact match first, then by population
        query += """
            ORDER BY 
                CASE 
                    WHEN name ILIKE %s THEN 0
                    WHEN asciiname ILIKE %s THEN 1
                    ELSE 2
                END,
                population DESC NULLS LAST
            LIMIT %s
        """
        params.extend([q, q, limit])
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        places = [Place(**dict(row)) for row in results]
        
        logger.info(f"Search for '{q}' returned {len(places)} results")
        
        return GeocodeResponse(places=places, count=len(places))
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/nearby", response_model=GeocodeResponse)
async def find_nearby(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius_km: float = Query(10, ge=0.1, le=100, description="Search radius in kilometers"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results to return"),
    feature_class: Optional[str] = Query(None, description="Filter by feature class")
):
    """
    Find places near given coordinates within specified radius
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convert km to degrees (approximate at UK latitudes)
        # 1 degree latitude ≈ 111 km
        # 1 degree longitude ≈ 70 km (at 52°N)
        radius_degrees = radius_km / 111.0
        
        query = """
            SELECT 
                geonameid, name, latitude, longitude,
                feature_class, feature_code, population,
                admin1_code as admin1, admin2_code as admin2,
                ST_Distance(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) * 111 as distance_km
            FROM geonames
            WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s)
        """
        params = [lon, lat, lon, lat, radius_degrees]
        
        if feature_class:
            query += " AND feature_class = %s"
            params.append(feature_class)
        
        query += " ORDER BY distance_km LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        places = [Place(**{k: v for k, v in dict(row).items() if k != 'distance_km'}) for row in results]
        
        logger.info(f"Found {len(places)} places within {radius_km}km of ({lat}, {lon})")
        
        return GeocodeResponse(places=places, count=len(places))
        
    except Exception as e:
        logger.error(f"Nearby search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reverse")
async def reverse_geocode(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude")
):
    """
    Reverse geocode - find the nearest place name to coordinates
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find nearest populated place
        cursor.execute("""
            SELECT 
                geonameid, name, latitude, longitude,
                feature_class, feature_code, population,
                admin1_code as admin1, admin2_code as admin2,
                ST_Distance(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) * 111 as distance_km
            FROM geonames
            WHERE feature_class = 'P'
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            LIMIT 1
        """, (lon, lat, lon, lat))
        
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="No nearby place found")
        
        place = Place(**{k: v for k, v in dict(result).items() if k != 'distance_km'})
        distance = result['distance_km']
        
        logger.info(f"Reverse geocode ({lat}, {lon}) -> {place.name} ({distance:.2f}km)")
        
        return {
            "place": place,
            "distance_km": round(distance, 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reverse geocode error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
