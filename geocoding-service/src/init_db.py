"""
GeoNames Database Initialization
Loads UK place names from GeoNames into PostGIS
"""
import os
import csv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database connection
DB_HOST = os.getenv("POSTGRES_HOST", "postgis")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "mapping_db")
DB_USER = os.getenv("POSTGRES_USER", "mapuser")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mappass123")

GEONAMES_FILE = "/app/data/geonames/GB.txt"

def init_geonames_table():
    """Create the geonames table if it doesn't exist"""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS geonames (
            geonameid INTEGER PRIMARY KEY,
            name VARCHAR(200),
            asciiname VARCHAR(200),
            alternatenames TEXT,
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            feature_class CHAR(1),
            feature_code VARCHAR(10),
            country_code CHAR(2),
            admin1_code VARCHAR(20),
            admin2_code VARCHAR(80),
            admin3_code VARCHAR(20),
            admin4_code VARCHAR(20),
            population BIGINT,
            elevation INTEGER,
            dem INTEGER,
            timezone VARCHAR(40),
            modification_date DATE,
            geom GEOMETRY(Point, 4326)
        )
    """)
    
    # Create spatial index
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_geonames_geom 
        ON geonames USING GIST(geom)
    """)
    
    # Create name search index
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_geonames_name 
        ON geonames(name)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_geonames_asciiname 
        ON geonames(asciiname)
    """)
    
    # Create feature class index
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_geonames_feature 
        ON geonames(feature_class, feature_code)
    """)
    
    print("✓ GeoNames table created")
    
    cursor.close()
    conn.close()

def import_geonames_data():
    """Import GeoNames data from file"""
    if not os.path.exists(GEONAMES_FILE):
        print(f"Error: {GEONAMES_FILE} not found!")
        return
    
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    
    # Check if already imported
    cursor.execute("SELECT COUNT(*) FROM geonames")
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"✓ GeoNames already has {count} records, skipping import")
        cursor.close()
        conn.close()
        return
    
    print(f"Importing GeoNames data from {GEONAMES_FILE}...")
    
    imported = 0
    skipped = 0
    
    with open(GEONAMES_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        
        batch = []
        batch_size = 1000
        
        for row in reader:
            try:
                # GeoNames format:
                # 0:geonameid, 1:name, 2:asciiname, 3:alternatenames, 4:latitude, 5:longitude,
                # 6:feature_class, 7:feature_code, 8:country_code, 9:cc2, 10:admin1, 11:admin2,
                # 12:admin3, 13:admin4, 14:population, 15:elevation, 16:dem, 17:timezone, 18:modification
                
                if len(row) < 19:
                    skipped += 1
                    continue
                
                geonameid = int(row[0])
                name = row[1]
                asciiname = row[2]
                alternatenames = row[3]
                latitude = float(row[4])
                longitude = float(row[5])
                feature_class = row[6]
                feature_code = row[7]
                country_code = row[8]
                admin1 = row[10]
                admin2 = row[11]
                admin3 = row[12]
                admin4 = row[13]
                population = int(row[14]) if row[14] else 0
                elevation = int(row[15]) if row[15] else None
                dem = int(row[16]) if row[16] else None
                timezone = row[17]
                mod_date = row[18]
                
                batch.append((
                    geonameid, name, asciiname, alternatenames, latitude, longitude,
                    feature_class, feature_code, country_code, admin1, admin2, admin3,
                    admin4, population, elevation, dem, timezone, mod_date,
                    longitude, latitude  # For ST_SetSRID(ST_MakePoint())
                ))
                
                if len(batch) >= batch_size:
                    cursor.executemany("""
                        INSERT INTO geonames (
                            geonameid, name, asciiname, alternatenames, latitude, longitude,
                            feature_class, feature_code, country_code, admin1_code, admin2_code,
                            admin3_code, admin4_code, population, elevation, dem, timezone,
                            modification_date, geom
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                        )
                    """, batch)
                    conn.commit()
                    imported += len(batch)
                    print(f"  Imported {imported} records...", end='\r')
                    batch = []
                    
            except Exception as e:
                skipped += 1
                continue
        
        # Import remaining batch
        if batch:
            cursor.executemany("""
                INSERT INTO geonames (
                    geonameid, name, asciiname, alternatenames, latitude, longitude,
                    feature_class, feature_code, country_code, admin1_code, admin2_code,
                    admin3_code, admin4_code, population, elevation, dem, timezone,
                    modification_date, geom
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                )
            """, batch)
            conn.commit()
            imported += len(batch)
    
    print(f"\n✓ Imported {imported} GeoNames records")
    print(f"  Skipped {skipped} invalid records")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    print("Initializing GeoNames database...")
    init_geonames_table()
    import_geonames_data()
    print("✓ GeoNames initialization complete!")
