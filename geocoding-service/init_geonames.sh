#!/bin/bash

# Wait for database
echo "Waiting for PostGIS database..."
sleep 10

# Download and import GeoNames data if not already done
if [ ! -f /app/data/geonames/.imported ]; then
    echo "Downloading GeoNames UK data..."
    cd /app/data/geonames
    
    # Download GB.zip (United Kingdom)
    if [ ! -f GB.zip ]; then
        wget -q http://download.geonames.org/export/dump/GB.zip
        unzip -q GB.zip
    fi
    
    echo "Initializing GeoNames database..."
    python3 /app/src/init_db.py
    
    touch /app/data/geonames/.imported
    echo "GeoNames data imported successfully!"
else
    echo "GeoNames data already imported, skipping..."
fi

# Start the FastAPI service
echo "Starting Geocoding Service..."
python3 /app/src/main.py
