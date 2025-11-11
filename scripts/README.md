# Setup Scripts

This directory contains setup and utility scripts for LLM Planner.

## Scripts

### download_models.py

Downloads all required AI models:
- Llama 3.1 8B (via Ollama)
- Whisper base model
- Sentence-transformers embedding model

**Usage:**
```powershell
python scripts/download_models.py
```

**Requirements:**
- Ollama installed (https://ollama.ai)
- Python 3.11+
- ~8GB free disk space
- Internet connection

### download_map_tiles.py

Downloads OpenStreetMap tiles for offline use.

**Usage:**
```powershell
# Download OSM tiles for London
python scripts/download_map_tiles.py --region london

# Download satellite imagery
python scripts/download_map_tiles.py --region london --layer satellite

# Download both
python scripts/download_map_tiles.py --region london --both
```

**Options:**
- `--region`: Region to download (default: london)
- `--layer`: Layer type - osm or satellite (default: osm)
- `--both`: Download both OSM and satellite layers

**Note:** Tile downloading may take 30-60 minutes depending on zoom levels and internet speed.

## Initial Setup

Run these scripts in order:

1. **Download Models:**
   ```powershell
   python scripts/download_models.py
   ```

2. **Download Map Tiles:**
   ```powershell
   python scripts/download_map_tiles.py --region london --both
   ```

3. **Start Services:**
   ```powershell
   docker-compose up -d
   ```

4. **Access Application:**
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - Login: admin / admin

## Troubleshooting

### Ollama Installation Issues

If Ollama is not found:
1. Download from https://ollama.ai
2. Install and restart your terminal
3. Verify with: `ollama --version`

### Tile Download Fails

If tile downloads fail:
- Check internet connection
- Wait a few minutes (rate limiting)
- Retry the command
- Tiles already downloaded will be skipped

### Python Dependencies

If Python packages fail to install:
```powershell
pip install --upgrade pip
pip install torch sentence-transformers openai-whisper requests
```

## Data Directories

After running setup scripts, you should have:

```
LLM_Planner/
├── models/
│   ├── llm/           # Ollama models
│   ├── whisper/       # Whisper models
│   └── embeddings/    # Sentence-transformers
└── map-tiles/
    ├── osm/           # OpenStreetMap tiles
    └── satellite/     # Satellite imagery
```
