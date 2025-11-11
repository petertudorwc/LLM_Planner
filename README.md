# LLM Planner - AI-Powered Disaster Relief Planning System

A standalone, offline-capable AI planning tool designed for disaster relief and emergency command centers. The system enables natural language interaction with mapping and data visualization capabilities.

## 🎯 Features

- **Natural Language Interface**: Chat with the AI using text or voice
- **Interactive Mapping**: Visualize data on OpenStreetMap with satellite imagery
- **Offline Operation**: All services run locally without internet dependency
- **Vector Search**: Semantic search over your document collections
- **Multi-format Support**: Ingest PDFs, Word, Excel, CSV, and geospatial data
- **Microservices Architecture**: Scalable Docker-based deployment

## 🏗️ Architecture

The system consists of 9 microservices:

1. **API Gateway** - Central orchestrator (FastAPI)
2. **LLM Service** - Ollama with Qwen3 8B
3. **Embedding Service** - sentence-transformers (all-mpnet-base-v2)
4. **Vector Store** - Qdrant for semantic search
5. **Mapping Service** - PostGIS + Leaflet API
6. **Speech Service** - Whisper speech-to-text
7. **Ingestion Service** - Document processing pipeline
8. **Frontend** - React web application
9. **Authentication** - JWT-based auth system

## 📋 Prerequisites

- Docker Desktop with WSL2 (Windows)
- NVIDIA GPU with CUDA support (RTX 3080 recommended)
- 64GB RAM recommended
- ~100GB free disk space for models and data

## 🚀 Quick Start

### 1. Clone the Repository

```bash
cd c:\Users\Peter\code\LLM_Planner
```

### 2. Download Models and Map Tiles

```bash
# Download LLM model (Qwen3 8B)
python scripts/download_models.py

# Download map tiles for London region
python scripts/download_map_tiles.py --region london
```

### 3. Start All Services

```bash
docker-compose up -d
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **API Gateway**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

Default login:
- Username: `admin`
- Password: `admin` (change after first login)

## 📦 Services and Ports

| Service | Port | Purpose |
|---------|------|---------|
| Frontend | 3000 | React web UI |
| API Gateway | 8000 | Main API endpoint |
| LLM Service | 8001 | Language model |
| Embedding Service | 8002 | Text embeddings |
| Mapping Service | 8003 | Map data API |
| Speech Service | 8004 | Voice recognition |
| Ingestion Service | 8005 | Document processing |
| Qdrant | 6333 | Vector database |
| PostGIS | 5432 | Spatial database |

## 📚 Usage Examples

### Chat with the System

```
User: "Show me all incidents in central London from last month"
```

### Upload Documents

1. Navigate to the "Upload" section
2. Select PDF, Word, Excel, or CSV files
3. System automatically processes and indexes content

### Voice Commands

1. Click the microphone button
2. Speak your query
3. System transcribes and processes

## 🛠️ Development

### Project Structure

```
LLM_Planner/
├── docker-compose.yml
├── .env
├── api-gateway/
├── llm-service/
├── embedding-service/
├── mapping-service/
├── speech-service/
├── ingestion-service/
├── frontend/
├── scripts/
├── data/
└── models/
```

### Building Individual Services

```bash
docker-compose build api-gateway
docker-compose up api-gateway
```

### Viewing Logs

```bash
docker-compose logs -f api-gateway
```

### Stopping Services

```bash
docker-compose down
```

## 🗺️ Map Configuration

The system is pre-configured for London/UK region. To change:

1. Edit `.env` file:
   ```
   MAP_REGION=your_region
   MAP_CENTER_LAT=your_latitude
   MAP_CENTER_LON=your_longitude
   ```

2. Download new map tiles:
   ```bash
   python scripts/download_map_tiles.py --region your_region
   ```

## 📊 Sample Data

Sample datasets for testing are available in `data/samples/`:
- London crime statistics
- Traffic incidents
- Weather data
- Borough boundaries (GeoJSON)

## 🔒 Security

- Change default JWT_SECRET in `.env`
- Change default admin password on first login
- Keep system updated with latest Docker images
- Run on isolated network for production

## 🐛 Troubleshooting

### GPU Not Detected

```bash
# Check NVIDIA Docker runtime
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Service Won't Start

```bash
# Check logs
docker-compose logs service-name

# Restart specific service
docker-compose restart service-name
```

### Out of Memory

Reduce model size in `.env`:
```
LLM_MODEL_NAME=llama3.1:8b
WHISPER_MODEL_SIZE=base
```

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

This is a private project currently. For questions, contact the development team.

## 📞 Support

For issues or questions, please create an issue in the repository.

---

**Version**: 1.0.0-POC  
**Last Updated**: November 2025
