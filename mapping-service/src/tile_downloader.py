import asyncio
import aiohttp
import os
import logging
from pathlib import Path
from typing import Tuple, List
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TileDownloader:
    """Download map tiles for offline use"""
    
    def __init__(self, tile_dir: str = "/app/map-tiles"):
        self.tile_dir = Path(tile_dir)
        self.tile_dir.mkdir(parents=True, exist_ok=True)
        
    def lat_lon_to_tile(self, lat: float, lon: float, zoom: int) -> Tuple[int, int]:
        """Convert lat/lon to tile coordinates"""
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return (x, y)
    
    def get_tile_bounds(self, lat1: float, lon1: float, lat2: float, lon2: float, zoom: int) -> List[Tuple[int, int]]:
        """Get all tiles needed to cover a bounding box"""
        x1, y1 = self.lat_lon_to_tile(lat1, lon1, zoom)
        x2, y2 = self.lat_lon_to_tile(lat2, lon2, zoom)
        
        # Ensure correct order
        x_min, x_max = min(x1, x2), max(x1, x2)
        y_min, y_max = min(y1, y2), max(y1, y2)
        
        tiles = []
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                tiles.append((x, y))
        
        return tiles
    
    async def download_tile(self, session: aiohttp.ClientSession, layer: str, z: int, x: int, y: int, url_template: str) -> bool:
        """Download a single tile"""
        tile_path = self.tile_dir / layer / str(z) / str(x)
        tile_path.mkdir(parents=True, exist_ok=True)
        tile_file = tile_path / f"{y}.png"
        
        # Skip if already exists
        if tile_file.exists():
            logger.debug(f"Tile already exists: {layer}/{z}/{x}/{y}")
            return True
        
        # Format URL
        url = url_template.format(z=z, x=x, y=y, s='a')  # Use 'a' subdomain for OSM
        
        try:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(tile_file, 'wb') as f:
                        f.write(content)
                    logger.info(f"Downloaded: {layer}/{z}/{x}/{y}")
                    return True
                else:
                    logger.warning(f"Failed to download {layer}/{z}/{x}/{y}: HTTP {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Error downloading {layer}/{z}/{x}/{y}: {e}")
            return False
    
    async def download_area(self, layer: str, url_template: str, lat1: float, lon1: float, 
                           lat2: float, lon2: float, zoom_levels: List[int], 
                           max_concurrent: int = 10):
        """Download tiles for a geographic area"""
        connector = aiohttp.TCPConnector(limit=max_concurrent)
        async with aiohttp.ClientSession(connector=connector) as session:
            for zoom in zoom_levels:
                tiles = self.get_tile_bounds(lat1, lon1, lat2, lon2, zoom)
                total = len(tiles)
                logger.info(f"Downloading {total} tiles for zoom level {zoom}")
                
                # Download tiles in batches
                tasks = []
                for i, (x, y) in enumerate(tiles):
                    task = self.download_tile(session, layer, zoom, x, y, url_template)
                    tasks.append(task)
                    
                    # Process in batches to avoid overwhelming the server
                    if len(tasks) >= max_concurrent or i == total - 1:
                        results = await asyncio.gather(*tasks)
                        success_count = sum(1 for r in results if r)
                        logger.info(f"Zoom {zoom}: {success_count}/{len(tasks)} tiles downloaded")
                        tasks = []
                        
                        # Small delay between batches
                        await asyncio.sleep(1)

# Predefined tile sources
TILE_SOURCES = {
    "osm": {
        "name": "OpenStreetMap",
        "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "OpenStreetMap contributors",
        "max_zoom": 19
    },
    "satellite": {
        "name": "ESRI World Imagery",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Esri",
        "max_zoom": 19
    }
}

async def download_tiles_for_area(area_name: str, bounds: dict, zoom_levels: List[int] = None):
    """
    Download tiles for a named area
    
    Args:
        area_name: Name of the area (e.g., "abingdon")
        bounds: Dictionary with keys: lat_min, lon_min, lat_max, lon_max
        zoom_levels: List of zoom levels to download (default: [10-15] for local area)
    """
    if zoom_levels is None:
        zoom_levels = list(range(10, 16))  # Good range for local area mapping
    
    downloader = TileDownloader()
    
    # Download both OSM and satellite tiles
    for layer_name, config in TILE_SOURCES.items():
        logger.info(f"Downloading {layer_name} tiles for {area_name}")
        logger.info(f"Bounds: {bounds}")
        logger.info(f"Zoom levels: {zoom_levels}")
        
        await downloader.download_area(
            layer=layer_name,
            url_template=config["url"],
            lat1=bounds["lat_min"],
            lon1=bounds["lon_min"],
            lat2=bounds["lat_max"],
            lon2=bounds["lon_max"],
            zoom_levels=zoom_levels,
            max_concurrent=10
        )
        
        logger.info(f"Completed downloading {layer_name} tiles for {area_name}")

# Example usage
if __name__ == "__main__":
    # Abingdon area bounds (adjust as needed)
    abingdon_bounds = {
        "lat_min": 51.63,
        "lon_min": -1.35,
        "lat_max": 51.71,
        "lon_max": -1.22
    }
    
    # Download tiles for zoom levels 12-16 (good detail for disaster relief)
    asyncio.run(download_tiles_for_area("abingdon", abingdon_bounds, zoom_levels=[12, 13, 14, 15, 16]))
