"""
Download OpenStreetMap tiles for offline use

This script downloads map tiles for the London region at zoom levels 10-16
"""

import os
import sys
import requests
from pathlib import Path
import time
import argparse

# Tile URL templates
OSM_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
SATELLITE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

# London bounding box
REGIONS = {
    "london": {
        "name": "London, UK",
        "bounds": {
            "north": 51.7,
            "south": 51.3,
            "east": 0.3,
            "west": -0.5
        },
        "zoom_levels": [10, 11, 12, 13, 14, 15, 16]
    }
}

def deg2num(lat_deg, lon_deg, zoom):
    """Convert lat/lon to tile numbers"""
    import math
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def download_tile(url, output_path):
    """Download a single tile"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if output_path.exists():
        return True  # Already downloaded
    
    try:
        headers = {
            'User-Agent': 'LLM Planner Map Downloader (disaster relief planning tool)'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        else:
            return False
    except Exception as e:
        print(f"Error downloading tile: {e}")
        return False

def download_region(region_name, layer="osm"):
    """Download all tiles for a region"""
    if region_name not in REGIONS:
        print(f"❌ Unknown region: {region_name}")
        print(f"Available regions: {', '.join(REGIONS.keys())}")
        return False
    
    region = REGIONS[region_name]
    bounds = region["bounds"]
    zoom_levels = region["zoom_levels"]
    
    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║         Downloading Map Tiles for {region['name']:<20}   ║
    ║                                                          ║
    ║  Layer: {layer:<50} ║
    ║  Zoom levels: {min(zoom_levels)}-{max(zoom_levels):<43} ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Calculate total tiles
    total_tiles = 0
    for zoom in zoom_levels:
        x1, y1 = deg2num(bounds["north"], bounds["west"], zoom)
        x2, y2 = deg2num(bounds["south"], bounds["east"], zoom)
        total_tiles += (x2 - x1 + 1) * (y2 - y1 + 1)
    
    print(f"📊 Total tiles to download: {total_tiles}")
    print(f"⏱️  Estimated time: {total_tiles * 0.5 / 60:.1f} minutes\n")
    
    # Create output directory
    tiles_dir = Path(__file__).parent.parent / "map-tiles" / layer
    tiles_dir.mkdir(parents=True, exist_ok=True)
    
    # Download tiles
    downloaded = 0
    skipped = 0
    failed = 0
    
    url_template = OSM_URL if layer == "osm" else SATELLITE_URL
    
    for zoom in zoom_levels:
        x1, y1 = deg2num(bounds["north"], bounds["west"], zoom)
        x2, y2 = deg2num(bounds["south"], bounds["east"], zoom)
        
        print(f"📥 Downloading zoom level {zoom}...")
        
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                output_path = tiles_dir / str(zoom) / str(x) / f"{y}.png"
                
                if output_path.exists():
                    skipped += 1
                    continue
                
                url = url_template.format(z=zoom, x=x, y=y)
                
                if download_tile(url, output_path):
                    downloaded += 1
                else:
                    failed += 1
                
                # Progress update
                if (downloaded + skipped + failed) % 100 == 0:
                    progress = (downloaded + skipped + failed) / total_tiles * 100
                    print(f"  Progress: {progress:.1f}% ({downloaded} new, {skipped} cached, {failed} failed)")
                
                # Rate limiting - be nice to tile servers
                time.sleep(0.1)
    
    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║                 ✅ Download Complete!                    ║
    ║                                                          ║
    ║  Downloaded: {downloaded:<44} ║
    ║  Cached:     {skipped:<44} ║
    ║  Failed:     {failed:<44} ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    return failed == 0

def main():
    parser = argparse.ArgumentParser(description="Download map tiles for offline use")
    parser.add_argument("--region", default="london", help="Region to download (default: london)")
    parser.add_argument("--layer", default="osm", choices=["osm", "satellite"], 
                       help="Layer type (default: osm)")
    parser.add_argument("--both", action="store_true", 
                       help="Download both OSM and satellite layers")
    
    args = parser.parse_args()
    
    if args.both:
        print("📦 Downloading both OSM and satellite layers...\n")
        success_osm = download_region(args.region, "osm")
        success_sat = download_region(args.region, "satellite")
        return success_osm and success_sat
    else:
        return download_region(args.region, args.layer)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
