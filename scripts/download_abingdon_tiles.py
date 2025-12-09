"""
Download map tiles for Abingdon area (5 mile radius)
This script downloads tiles respectfully with rate limiting to avoid being blocked by OSM.
"""

import asyncio
import aiohttp
import os
import math
import time
import random
from pathlib import Path

# Abingdon center coordinates
ABINGDON_LAT = 51.6707
ABINGDON_LON = -1.2879

# Abingdon Airfield coordinates
AIRFIELD_LAT = 51.6997
AIRFIELD_LON = -1.2831

# 5 miles = 8.05 km radius
RADIUS_KM = 8.05

# Zoom levels to download (11-15 gives good coverage without too many tiles)
ZOOM_LEVELS = [11, 12, 13, 14, 15 , 16, 17]

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "map-tiles"

# Tile sources
TILE_SOURCES = {
    "osm": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    "satellite": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
}

# Rate limiting: Human-like browsing speed
# Average 1 request every 3-5 seconds (much slower to avoid rate limiting)
MIN_DELAY_BETWEEN_REQUESTS = 3.0  # Minimum 3 seconds
MAX_DELAY_BETWEEN_REQUESTS = 5.0  # Maximum 5 seconds
MAX_CONCURRENT_REQUESTS = 1  # Only 1 request at a time (like a single browser tab)

# Blocked tile detection
# OSM serves a specific placeholder image when rate limiting
# This image is EXACTLY 7412 bytes for OSM tiles
BLOCKED_TILE_SIZE = 7412  # Exact size of OSM's rate limit placeholder image

# User agent (required by OSM)
USER_AGENT = "DisasterReliefApp/1.0 (Emergency Planning Tool)"


def lat_lon_to_tile(lat, lon, zoom):
    """Convert lat/lon to tile coordinates"""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tile_to_lat_lon(x, y, zoom):
    """Convert tile coordinates to lat/lon"""
    n = 2.0 ** zoom
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lat, lon


def get_tiles_in_radius(center_lat, center_lon, radius_km, zoom):
    """Get all tile coordinates within radius of center point"""
    # Convert radius to degrees (approximate)
    # At this latitude, 1 degree lat ≈ 111 km, 1 degree lon ≈ 70 km
    radius_lat = radius_km / 111.0
    radius_lon = radius_km / 70.0
    
    # Get bounding box
    lat_min = center_lat - radius_lat
    lat_max = center_lat + radius_lat
    lon_min = center_lon - radius_lon
    lon_max = center_lon + radius_lon
    
    # Get tile coordinates for corners
    x_min, y_max = lat_lon_to_tile(lat_min, lon_min, zoom)
    x_max, y_min = lat_lon_to_tile(lat_max, lon_max, zoom)
    
    tiles = []
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            # Check if tile center is within radius
            tile_lat, tile_lon = tile_to_lat_lon(x + 0.5, y + 0.5, zoom)
            
            # Calculate distance using Haversine formula
            lat1_rad = math.radians(center_lat)
            lat2_rad = math.radians(tile_lat)
            delta_lat = math.radians(tile_lat - center_lat)
            delta_lon = math.radians(tile_lon - center_lon)
            
            a = (math.sin(delta_lat / 2) ** 2 + 
                 math.cos(lat1_rad) * math.cos(lat2_rad) * 
                 math.sin(delta_lon / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance_km = 6371 * c  # Earth radius in km
            
            if distance_km <= radius_km:
                tiles.append((x, y))
    
    return tiles


async def download_tile(session, layer, zoom, x, y, redownload_small=False):
    """Download a single tile"""
    # Get URL template
    if layer == "osm":
        # Use different subdomains for load balancing
        subdomain = ['a', 'b', 'c'][hash(f"{x}{y}") % 3]
        url = TILE_SOURCES[layer].format(s=subdomain, z=zoom, x=x, y=y)
    else:
        url = TILE_SOURCES[layer].format(z=zoom, x=x, y=y)
    
    # Output path
    tile_dir = OUTPUT_DIR / layer / str(zoom) / str(x)
    tile_path = tile_dir / f"{y}.png"
    
    # Check if file exists
    if tile_path.exists():
        file_size = tile_path.stat().st_size
        
        # Check if it's the exact blocked tile size
        is_blocked = (file_size == BLOCKED_TILE_SIZE)
        
        # If it's a blocked tile and we're redownloading
        if is_blocked and redownload_small:
            print(f"🔄 Re-downloading {layer}/{zoom}/{x}/{y} (blocked tile: {file_size} bytes = BLOCKED_TILE_SIZE)")
        # If it's a good tile, skip
        elif not is_blocked:
            print(f"✓ Skipping {layer}/{zoom}/{x}/{y} (already have good tile: {file_size} bytes)")
            return True
        # If it's blocked but we're not redownloading, skip
        elif not redownload_small:
            print(f"⚠ Skipping {layer}/{zoom}/{x}/{y} (blocked tile: {file_size} bytes = BLOCKED_TILE_SIZE, use option 2 to re-download)")
            return False
    
    # Create directory
    tile_dir.mkdir(parents=True, exist_ok=True)
    
    # Always add delay BEFORE making request (human-like behavior)
    delay = random.uniform(MIN_DELAY_BETWEEN_REQUESTS, MAX_DELAY_BETWEEN_REQUESTS)
    print(f"  ⏳ Waiting {delay:.1f}s before downloading {layer}/{zoom}/{x}/{y}...")
    await asyncio.sleep(delay)
    
    try:
        print(f"  🌐 Requesting {url[:80]}...")
        headers = {"User-Agent": USER_AGENT}
        async with session.get(url, headers=headers, timeout=30) as response:
            print(f"  📡 Response status: {response.status}")
            if response.status == 200:
                content = await response.read()
                content_length = len(content)
                print(f"  📦 Received {content_length} bytes")
                
                # Check if it's the blocked tile (exact size match)
                if content_length == BLOCKED_TILE_SIZE:
                    # Save it anyway so we can verify
                    with open(tile_path, 'wb') as f:
                        f.write(content)
                    print(f"❌ BLOCKED: Server returned blocked tile ({content_length} bytes = BLOCKED_TILE_SIZE) for {layer}/{zoom}/{x}/{y}")
                    print(f"  💾 Saved blocked image to: {tile_path}")
                    return False
                else:
                    # Good tile - save it
                    with open(tile_path, 'wb') as f:
                        f.write(content)
                    print(f"✅ SUCCESS: Downloaded {layer}/{zoom}/{x}/{y} ({content_length} bytes)")
                    return True
            else:
                print(f"❌ HTTP ERROR: Status {response.status} for {layer}/{zoom}/{x}/{y}")
                return False
    except asyncio.TimeoutError:
        print(f"❌ TIMEOUT: Request timed out after 30s for {layer}/{zoom}/{x}/{y}")
        return False
    except Exception as e:
        print(f"❌ EXCEPTION: {type(e).__name__}: {e} for {layer}/{zoom}/{x}/{y}")
        return False


async def download_area_tiles(center_lat, center_lon, area_name, redownload_small=False):
    """Download tiles for an area"""
    print(f"\n{'='*60}")
    print(f"Downloading tiles for {area_name}")
    print(f"Center: {center_lat}, {center_lon}")
    print(f"Radius: {RADIUS_KM} km (5 miles)")
    print(f"Zoom levels: {ZOOM_LEVELS}")
    if redownload_small:
        print("Mode: RE-DOWNLOADING blocked/small tiles")
    print(f"{'='*60}\n")
    
    # Calculate total tiles
    total_tiles = 0
    for zoom in ZOOM_LEVELS:
        tiles = get_tiles_in_radius(center_lat, center_lon, RADIUS_KM, zoom)
        total_tiles += len(tiles) * 2  # OSM + Satellite
        print(f"Zoom {zoom}: {len(tiles)} tiles per layer")
    
    print(f"\nTotal tiles to download: {total_tiles}")
    avg_delay = (MIN_DELAY_BETWEEN_REQUESTS + MAX_DELAY_BETWEEN_REQUESTS) / 2
    print(f"Estimated time (avg {avg_delay:.1f}s per tile): {total_tiles * avg_delay / 60:.1f} minutes\n")
    
    # Ask for confirmation
    if not redownload_small:
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
    
    # Download tiles (one at a time, sequentially - like a human browsing)
    total_downloaded = 0
    total_skipped_good = 0
    total_skipped_blocked = 0
    total_blocked = 0
    total_errors = 0
    
    async with aiohttp.ClientSession() as session:
        for zoom in ZOOM_LEVELS:
            tiles = get_tiles_in_radius(center_lat, center_lon, RADIUS_KM, zoom)
            
            print(f"\n--- Downloading zoom level {zoom} ({len(tiles)} tiles per layer) ---")
            
            # Download OSM tiles (one at a time)
            print(f"\nOSM tiles:")
            success = 0
            for i, (x, y) in enumerate(tiles, 1):
                print(f"\n[{i}/{len(tiles)}] Processing osm/{zoom}/{x}/{y}")
                result = await download_tile(session, "osm", zoom, x, y, redownload_small)
                if result is True:
                    success += 1
                    total_downloaded += 1
                elif result is False:
                    total_blocked += 1
            print(f"\n📊 OSM zoom {zoom}: {success}/{len(tiles)} successful")
            
            # Download satellite tiles (one at a time)
            print(f"\nSatellite tiles:")
            success = 0
            for i, (x, y) in enumerate(tiles, 1):
                print(f"\n[{i}/{len(tiles)}] Processing satellite/{zoom}/{x}/{y}")
                result = await download_tile(session, "satellite", zoom, x, y, redownload_small)
                if result is True:
                    success += 1
                    total_downloaded += 1
                elif result is False:
                    total_blocked += 1
            print(f"\n📊 Satellite zoom {zoom}: {success}/{len(tiles)} successful")
    
    print(f"\n{'='*60}")
    print("DOWNLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successfully downloaded: {total_downloaded}")
    print(f"❌ Blocked/small images: {total_blocked}")
    print(f"ℹ️  Total processed: {total_downloaded + total_blocked}")
    print(f"{'='*60}\n")


async def main():
    """Main function"""
    print("Map Tile Downloader for Abingdon Area")
    print("="*60)
    print("\nOptions:")
    print("1. Download new tiles only")
    print("2. Re-download blocked/small tiles (fix corrupted downloads)")
    print("3. Check for blocked tiles without downloading")
    
    choice = input("\nSelect option (1/2/3): ").strip()
    
    if choice == "3":
        # Check for blocked tiles
        print("\nScanning for blocked/small tiles...")
        await check_blocked_tiles()
        return
    
    redownload_small = (choice == "2")
    
    if redownload_small:
        print(f"\n⚠️  WARNING: This will re-download all tiles that are exactly {BLOCKED_TILE_SIZE} bytes (OSM blocked tiles)")
        confirm = input("Are you sure? (y/n): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return
    
    # Download Abingdon center area
    await download_area_tiles(ABINGDON_LAT, ABINGDON_LON, "Abingdon Center", redownload_small)
    
    # Download Abingdon Airfield area
    print("\n")
    await download_area_tiles(AIRFIELD_LAT, AIRFIELD_LON, "Abingdon Airfield", redownload_small)


async def check_blocked_tiles():
    """Check for blocked tiles in the download directory (exact size match)"""
    print("\nScanning map-tiles directory for blocked tiles...\n")
    print(f"Looking for tiles exactly {BLOCKED_TILE_SIZE} bytes (OSM blocked tile size)\n")
    
    blocked_by_layer = {"osm": [], "satellite": []}
    
    for layer in ["osm", "satellite"]:
        layer_dir = OUTPUT_DIR / layer
        if not layer_dir.exists():
            continue
        
        for zoom_dir in layer_dir.iterdir():
            if not zoom_dir.is_dir():
                continue
            zoom = zoom_dir.name
            
            for x_dir in zoom_dir.iterdir():
                if not x_dir.is_dir():
                    continue
                x = x_dir.name
                
                for tile_file in x_dir.glob("*.png"):
                    y = tile_file.stem
                    file_size = tile_file.stat().st_size
                    
                    # Check for exact blocked tile size
                    if file_size == BLOCKED_TILE_SIZE:
                        blocked_by_layer[layer].append({
                            "zoom": zoom,
                            "x": x,
                            "y": y,
                            "size": file_size,
                            "path": str(tile_file)
                        })
    
    # Print results
    print(f"{'='*60}")
    print("BLOCKED/SMALL TILES REPORT")
    print(f"{'='*60}\n")
    
    for layer in ["osm", "satellite"]:
        blocked = blocked_by_layer[layer]
        print(f"{layer.upper()}: {len(blocked)} blocked tiles")
        
        if blocked:
            # Group by zoom level
            by_zoom = {}
            for tile in blocked:
                zoom = tile["zoom"]
                if zoom not in by_zoom:
                    by_zoom[zoom] = []
                by_zoom[zoom].append(tile)
            
            for zoom in sorted(by_zoom.keys()):
                tiles = by_zoom[zoom]
                print(f"  Zoom {zoom}: {len(tiles)} blocked")
                # Show first 5 examples
                for tile in tiles[:5]:
                    print(f"    - {layer}/{zoom}/{tile['x']}/{tile['y']} ({tile['size']} bytes)")
                if len(tiles) > 5:
                    print(f"    ... and {len(tiles) - 5} more")
        print()
    
    total_blocked = sum(len(v) for v in blocked_by_layer.values())
    print(f"Total blocked tiles: {total_blocked}")
    print(f"\nTo re-download these tiles, run the script and select option 2.")


if __name__ == "__main__":
    asyncio.run(main())
