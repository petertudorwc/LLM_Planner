#!/usr/bin/env python3
"""
Download base map tiles for entire UK (zoom levels 8-12)
Provides general overview coverage for users to browse before downloading detailed tiles

UK Bounding Box:
- North: 60.9°N (Shetland Islands)
- South: 49.9°N (Scilly Isles)
- West: -8.2°W (Western Ireland border)
- East: 1.8°E (East Anglia)

Zoom levels:
- 8: ~100 tiles (entire UK in a few tiles)
- 9: ~400 tiles (regional view)
- 10: ~1,000 tiles (county-level)
- 11: ~4,000 tiles (city-level)
- 12: ~16,000 tiles (district-level)
Total estimated: ~21,500 tiles per layer
"""

import os
import asyncio
import aiohttp
import random
import math
from pathlib import Path
from typing import Tuple, List

# UK Bounding Box
UK_NORTH = 60.9
UK_SOUTH = 49.9
UK_WEST = -8.2
UK_EAST = 1.8

# Zoom levels to download
ZOOM_LEVELS = [8, 9, 10, 11, 12]

# Rate limiting settings (same as Abingdon script)
BLOCKED_TILE_SIZE = 7412  # OSM's blocked tile placeholder size
MIN_DELAY_BETWEEN_REQUESTS = 3.0  # seconds
MAX_DELAY_BETWEEN_REQUESTS = 5.0  # seconds
MAX_CONCURRENT_REQUESTS = 1  # Sequential downloads only

# Base directory for tiles (relative to script location)
SCRIPT_DIR = Path(__file__).parent
BASE_TILE_DIR = SCRIPT_DIR.parent / "map-tiles"

# Tile server URLs
OSM_SERVERS = [
    "https://a.tile.openstreetmap.org",
    "https://b.tile.openstreetmap.org",
    "https://c.tile.openstreetmap.org"
]

SATELLITE_SERVER = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile"


def lat_lon_to_tile_coords(lat: float, lon: float, zoom: int) -> Tuple[int, int]:
    """Convert latitude/longitude to tile coordinates for a given zoom level"""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def get_tile_range(north: float, south: float, west: float, east: float, zoom: int) -> List[Tuple[int, int]]:
    """
    Get all tile coordinates within a bounding box for a given zoom level
    Returns list of (x, y) tuples
    """
    # Get corner tiles
    x_west, y_north = lat_lon_to_tile_coords(north, west, zoom)
    x_east, y_south = lat_lon_to_tile_coords(south, east, zoom)
    
    # Generate all tiles in range
    tiles = []
    for x in range(x_west, x_east + 1):
        for y in range(y_north, y_south + 1):
            tiles.append((x, y))
    
    return tiles


async def download_tile(session: aiohttp.ClientSession, layer: str, zoom: int, x: int, y: int, redownload_small: bool = False) -> dict:
    """
    Download a single tile with rate limiting
    Returns dict with result status
    """
    tile_path = BASE_TILE_DIR / layer / str(zoom) / str(x) / f"{y}.png"
    
    # Check if tile already exists
    if tile_path.exists():
        file_size = tile_path.stat().st_size
        
        # Check if it's a blocked tile
        if file_size == BLOCKED_TILE_SIZE:
            if redownload_small:
                print(f"  🔄 Re-downloading blocked tile {layer}/{zoom}/{x}/{y} ({BLOCKED_TILE_SIZE} bytes)")
            else:
                print(f"  ⚠️  Skipping blocked tile {layer}/{zoom}/{x}/{y} ({BLOCKED_TILE_SIZE} bytes)")
                return {"status": "blocked", "layer": layer, "zoom": zoom, "x": x, "y": y, "size": file_size}
        else:
            # Already have a good tile
            print(f"  ✓ Skipping {layer}/{zoom}/{x}/{y} (already have good tile: {file_size} bytes)")
            return {"status": "skipped", "layer": layer, "zoom": zoom, "x": x, "y": y, "size": file_size}
    
    # Add delay BEFORE making request (human-like behavior)
    delay = random.uniform(MIN_DELAY_BETWEEN_REQUESTS, MAX_DELAY_BETWEEN_REQUESTS)
    print(f"  ⏳ Waiting {delay:.1f}s before downloading {layer}/{zoom}/{x}/{y}...")
    await asyncio.sleep(delay)
    
    # Build URL based on layer
    if layer == "osm":
        server = random.choice(OSM_SERVERS)
        url = f"{server}/{zoom}/{x}/{y}.png"
    elif layer == "satellite":
        url = f"{SATELLITE_SERVER}/{zoom}/{y}/{x}"
    else:
        raise ValueError(f"Unknown layer: {layer}")
    
    # Download tile
    headers = {
        'User-Agent': 'DisasterReliefMappingSystem/1.0 (Training/Testing)'
    }
    
    try:
        print(f"  🌐 Requesting {url}...")
        async with session.get(url, headers=headers, timeout=30) as response:
            print(f"  📡 Response status: {response.status}")
            
            if response.status != 200:
                print(f"  ❌ FAILED: HTTP {response.status} for {layer}/{zoom}/{x}/{y}")
                return {"status": "failed", "layer": layer, "zoom": zoom, "x": x, "y": y, "error": f"HTTP {response.status}"}
            
            content = await response.read()
            content_length = len(content)
            print(f"  📦 Received {content_length} bytes")
            
            # Check if this is a blocked tile
            if content_length == BLOCKED_TILE_SIZE:
                print(f"  🚫 BLOCKED: Received blocked tile placeholder ({BLOCKED_TILE_SIZE} bytes) for {layer}/{zoom}/{x}/{y}")
                
                # Save it anyway so we know it's blocked
                tile_path.parent.mkdir(parents=True, exist_ok=True)
                with open(tile_path, 'wb') as f:
                    f.write(content)
                
                return {"status": "blocked", "layer": layer, "zoom": zoom, "x": x, "y": y, "size": content_length}
            
            # Save the tile
            tile_path.parent.mkdir(parents=True, exist_ok=True)
            with open(tile_path, 'wb') as f:
                f.write(content)
            
            print(f"  ✅ SUCCESS: Downloaded {layer}/{zoom}/{x}/{y} ({content_length} bytes)")
            return {"status": "success", "layer": layer, "zoom": zoom, "x": x, "y": y, "size": content_length}
            
    except asyncio.TimeoutError:
        print(f"  ⏱️  TIMEOUT: Request timed out for {layer}/{zoom}/{x}/{y}")
        return {"status": "timeout", "layer": layer, "zoom": zoom, "x": x, "y": y}
    except Exception as e:
        print(f"  ❌ ERROR: {str(e)} for {layer}/{zoom}/{x}/{y}")
        return {"status": "error", "layer": layer, "zoom": zoom, "x": x, "y": y, "error": str(e)}


async def download_zoom_level(layer: str, zoom: int, redownload_small: bool = False):
    """Download all tiles for a single zoom level within UK bounds"""
    print(f"\n{'='*80}")
    print(f"Downloading {layer.upper()} tiles at zoom level {zoom}")
    print(f"{'='*80}\n")
    
    # Get all tiles in UK bounding box
    tiles = get_tile_range(UK_NORTH, UK_SOUTH, UK_WEST, UK_EAST, zoom)
    total_tiles = len(tiles)
    
    print(f"📊 Total tiles to process: {total_tiles:,}")
    print(f"⏱️  Estimated time: {total_tiles * 4 / 60:.1f} minutes (at ~4s per tile)\n")
    
    # Statistics
    stats = {
        "success": 0,
        "skipped": 0,
        "blocked": 0,
        "failed": 0,
        "timeout": 0,
        "error": 0
    }
    
    # Create session with timeout
    timeout = aiohttp.ClientTimeout(total=60, connect=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Download tiles sequentially (one at a time)
        for idx, (x, y) in enumerate(tiles, 1):
            print(f"\n[{idx}/{total_tiles}] Processing {layer}/{zoom}/{x}/{y}")
            
            result = await download_tile(session, layer, zoom, x, y, redownload_small)
            stats[result["status"]] += 1
            
            # Progress update every 50 tiles
            if idx % 50 == 0:
                print(f"\n📊 Progress: {idx}/{total_tiles} ({idx/total_tiles*100:.1f}%)")
                print(f"   ✅ Success: {stats['success']}, ✓ Skipped: {stats['skipped']}, 🚫 Blocked: {stats['blocked']}")
                print(f"   ❌ Failed: {stats['failed']}, ⏱️  Timeout: {stats['timeout']}, ⚠️  Error: {stats['error']}\n")
    
    # Final statistics
    print(f"\n{'='*80}")
    print(f"✅ COMPLETED: {layer.upper()} zoom level {zoom}")
    print(f"{'='*80}")
    print(f"📊 Final Statistics:")
    print(f"   ✅ Success: {stats['success']:,}")
    print(f"   ✓ Skipped: {stats['skipped']:,}")
    print(f"   🚫 Blocked: {stats['blocked']:,}")
    print(f"   ❌ Failed: {stats['failed']:,}")
    print(f"   ⏱️  Timeout: {stats['timeout']:,}")
    print(f"   ⚠️  Error: {stats['error']:,}")
    print(f"{'='*80}\n")


async def download_uk_base_tiles(redownload_small: bool = False):
    """Download all base UK tiles (zoom levels 8-12) for both OSM and Satellite"""
    print("\n" + "="*80)
    print("🇬🇧 UK BASE MAP TILE DOWNLOADER")
    print("="*80)
    print(f"Zoom levels: {ZOOM_LEVELS}")
    print(f"Bounding box: {UK_NORTH}°N to {UK_SOUTH}°N, {UK_WEST}°W to {UK_EAST}°E")
    print(f"Rate limiting: {MIN_DELAY_BETWEEN_REQUESTS}-{MAX_DELAY_BETWEEN_REQUESTS}s between requests")
    print(f"Tile directory: {BASE_TILE_DIR}")
    print("="*80 + "\n")
    
    # Calculate total tiles
    total_tiles = 0
    for zoom in ZOOM_LEVELS:
        tiles = get_tile_range(UK_NORTH, UK_SOUTH, UK_WEST, UK_EAST, zoom)
        total_tiles += len(tiles) * 2  # OSM + Satellite
        print(f"Zoom {zoom:2d}: {len(tiles):5,} tiles per layer ({len(tiles)*2:5,} total)")
    
    print(f"\n📊 Grand Total: {total_tiles:,} tiles (both layers)")
    print(f"⏱️  Estimated time: {total_tiles * 4 / 3600:.1f} hours (at ~4s per tile)\n")
    
    input("Press Enter to start downloading...")
    
    # Download each zoom level for each layer
    for zoom in ZOOM_LEVELS:
        # Download OSM tiles
        await download_zoom_level("osm", zoom, redownload_small)
        
        # Download Satellite tiles
        await download_zoom_level("satellite", zoom, redownload_small)
    
    print("\n" + "="*80)
    print("🎉 ALL UK BASE TILES DOWNLOADED!")
    print("="*80)


def check_blocked_tiles():
    """Check for blocked tiles (exactly 7412 bytes) in the tile directory"""
    print("\n" + "="*80)
    print("🔍 CHECKING FOR BLOCKED TILES")
    print("="*80 + "\n")
    
    blocked_tiles = []
    
    for layer in ["osm", "satellite"]:
        layer_dir = BASE_TILE_DIR / layer
        if not layer_dir.exists():
            continue
        
        for tile_file in layer_dir.rglob("*.png"):
            if tile_file.stat().st_size == BLOCKED_TILE_SIZE:
                # Extract zoom/x/y from path
                parts = tile_file.relative_to(layer_dir).parts
                zoom = parts[0]
                x = parts[1]
                y = parts[2].replace('.png', '')
                blocked_tiles.append(f"{layer}/{zoom}/{x}/{y}")
    
    if blocked_tiles:
        print(f"🚫 Found {len(blocked_tiles)} blocked tiles ({BLOCKED_TILE_SIZE} bytes each):\n")
        for tile in blocked_tiles:
            print(f"   {tile}")
    else:
        print("✅ No blocked tiles found!")
    
    print("\n" + "="*80 + "\n")
    
    return blocked_tiles


async def main():
    """Main entry point"""
    import sys
    
    redownload_small = False
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--redownload-blocked":
            redownload_small = True
            print("🔄 Will re-download blocked tiles\n")
        elif sys.argv[1] == "--check-blocked":
            check_blocked_tiles()
            return
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python download_uk_base.py                  # Download UK base tiles (skip existing)")
            print("  python download_uk_base.py --redownload-blocked  # Re-download blocked tiles")
            print("  python download_uk_base.py --check-blocked  # Check for blocked tiles")
            return
    
    # Create base tile directory
    BASE_TILE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download UK base tiles
    await download_uk_base_tiles(redownload_small)
    
    # Check for blocked tiles after download
    check_blocked_tiles()


if __name__ == "__main__":
    asyncio.run(main())
