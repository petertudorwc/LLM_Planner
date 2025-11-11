# Geographic Data Sources for Disaster Relief Planning

## 1. GeoNames Database (Free & Comprehensive)

### Download UK Places
- URL: https://download.geonames.org/export/dump/
- File: `GB.zip` (United Kingdom data - ~2MB compressed)
- Contains: ~50,000+ UK place names with coordinates

### Fields in the data:
- geonameid
- name
- latitude
- longitude
- feature class/code (city, town, village, etc.)
- population
- admin codes (county, region)

### How to integrate:
1. Download `GB.zip` from GeoNames
2. Extract `GB.txt` 
3. Import into PostgreSQL/PostGIS database
4. Create an endpoint in ingestion-service to search places
5. LLM can call `search_places` function instead of hard-coded coordinates

## 2. OpenStreetMap Nominatim

### API-based (no download needed)
- URL: https://nominatim.openstreetmap.org/
- Example: https://nominatim.openstreetmap.org/search?q=Abingdon,UK&format=json
- Rate limit: 1 request/second for free tier

### Integration:
- Add `geocode_location` function to call Nominatim API
- Cache results in database to avoid repeated lookups

## 3. UK Ordnance Survey Open Data

### Official UK government data
- URL: https://www.ordnancesurvey.co.uk/products/os-open-names
- Format: CSV with ~2 million UK place names
- Very detailed (includes streets, districts, natural features)

## 4. For Disaster Relief Specific Data

### GADM (Global Administrative Areas)
- URL: https://gadm.org/download_country.html
- Provides administrative boundaries (counties, districts, wards)
- GeoJSON/Shapefile format ready for PostGIS

### Natural Earth Data
- URL: https://www.naturalearthdata.com/
- Cities, populated places, boundaries
- Multiple resolution levels (10m, 50m, 110m scale)

## Recommended Implementation

For your disaster relief system, I recommend:

1. **GeoNames GB.txt** - For basic place name lookup (~50K places)
2. **GADM boundaries** - For administrative regions
3. **Nominatim fallback** - For places not in your database

This gives you offline capability with fallback to online lookup.
