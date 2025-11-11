# Quick Start Guide

This guide will help you get LLM Planner up and running on your Windows machine.

## Prerequisites

Before starting, ensure you have:

- ✅ **Docker Desktop** with WSL2 backend
- ✅ **NVIDIA GPU** with CUDA support (RTX 3080 recommended)
- ✅ **64GB RAM** (32GB minimum)
- ✅ **100GB free disk space**
- ✅ **Python 3.11+**
- ✅ **Ollama** (https://ollama.ai)

## Step-by-Step Setup

### 1. Install Prerequisites

#### Install Docker Desktop
1. Download from https://www.docker.com/products/docker-desktop/
2. Install with WSL2 backend
3. Enable NVIDIA GPU support in Docker settings

#### Install Ollama
1. Download from https://ollama.ai
2. Run installer
3. Verify: `ollama --version`

#### Install Python Dependencies
```powershell
pip install torch sentence-transformers openai-whisper requests
```

### 2. Download Models

This downloads ~8GB of AI models (15-30 minutes):

```powershell
cd c:\Users\Peter\code\LLM_Planner
python scripts\download_models.py
```

**Model:** Qwen3 8B - Latest model with advanced function calling and thinking capabilities

### 3. Download Map Tiles

This downloads map tiles for London (30-60 minutes):

```powershell
python scripts\download_map_tiles.py --region london --both
```

### 4. Configure Environment

Edit `.env` file if needed (defaults are fine for testing):
```env
JWT_SECRET=change-this-to-a-secure-random-string-in-production
LLM_MODEL_NAME=llama3.1:8b
WHISPER_MODEL_SIZE=base
```

### 5. Start Services

Start all Docker containers:

```powershell
docker-compose up -d
```

This will start:
- API Gateway (port 8000)
- LLM Service (port 8001)
- Embedding Service (port 8002)
- Mapping Service (port 8003)
- Speech Service (port 8004)
- Ingestion Service (port 8005)
- Vector Store (port 6333)
- Frontend (port 3000)

### 6. Access the Application

Open your browser and go to:
**http://localhost:3000**

**Default Login:**
- Username: `admin`
- Password: `admin`

**Important:** Change the default password after first login!

## Using the Application

### Chat Interface

1. Click "Chat" in the sidebar
2. Type or speak your query
3. Press Enter or click Send

**Example queries:**
- "Show me incidents in central London"
- "Plot fire locations from last month"
- "Search for traffic accidents near Westminster"

### Voice Input

1. Click the microphone icon
2. Speak your query
3. Click again to stop recording
4. Text will appear in the input field

### Upload Documents

1. Click "Upload Data" in the sidebar
2. Select files (PDF, Word, Excel, CSV, GeoJSON)
3. Click "Upload and Process"
4. Documents are indexed and searchable

### Map View

1. Click "Map View" in the sidebar
2. Pan and zoom the map
3. Toggle between street and satellite views
4. See data plotted by the AI

## Checking Service Health

View logs for all services:
```powershell
docker-compose logs -f
```

View logs for specific service:
```powershell
docker-compose logs -f api-gateway
```

Check service status:
```powershell
docker-compose ps
```

## Stopping the System

Stop all services:
```powershell
docker-compose down
```

Stop and remove all data (careful!):
```powershell
docker-compose down -v
```

## Troubleshooting

### Services Won't Start

**Check Docker:**
```powershell
docker --version
docker ps
```

**Rebuild containers:**
```powershell
docker-compose build --no-cache
docker-compose up -d
```

### GPU Not Detected

**Check NVIDIA driver:**
```powershell
nvidia-smi
```

**Check Docker GPU support:**
```powershell
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Out of Memory

**Reduce model size in `.env`:**
```env
LLM_MODEL_NAME=qwen3:8b
WHISPER_MODEL_SIZE=tiny
```

**Or use an even smaller model:**
```env
LLM_MODEL_NAME=qwen3:4b
WHISPER_MODEL_SIZE=tiny
```

**Increase Docker memory:**
1. Open Docker Desktop
2. Settings → Resources
3. Increase memory limit

### Port Already in Use

**Find process using port:**
```powershell
netstat -ano | findstr :3000
```

**Kill process:**
```powershell
taskkill /PID <process_id> /F
```

### Can't Access Frontend

1. Check if frontend is running: `docker-compose ps`
2. Check logs: `docker-compose logs frontend`
3. Try rebuilding: `docker-compose build frontend`
4. Clear browser cache and retry

### API Errors

1. Check API Gateway logs: `docker-compose logs api-gateway`
2. Verify all services are healthy: http://localhost:8000/health
3. Check service connectivity: `docker-compose exec api-gateway ping llm-service`

## Performance Tips

### For Faster LLM Responses

1. Use smaller model for testing:
   ```env
   LLM_MODEL_NAME=qwen3:4b
   ```

2. Enable GPU acceleration (should be automatic with NVIDIA Docker)

3. For better quality, upgrade to larger model when hardware allows:
   ```env
   LLM_MODEL_NAME=qwen3:32b
   ```

### For Better Speech Recognition

1. Use higher quality Whisper model:
   ```env
   WHISPER_MODEL_SIZE=medium
   ```

2. Ensure microphone permissions in browser

### For Smoother Map Experience

1. Pre-download more zoom levels
2. Use SSD for tile storage
3. Increase browser cache size

## Next Steps

1. **Add Sample Data:**
   - Upload London crime statistics from Kaggle
   - Upload traffic incident reports
   - Upload weather data

2. **Customize the System:**
   - Add new data sources
   - Create custom map layers
   - Train the AI with domain-specific knowledge

3. **Scale Up:**
   - Upgrade to Llama 3.1 70B for better reasoning
   - Add more map regions
   - Deploy to dedicated server

## Getting Help

### View Documentation
- Main README: `README.md`
- API Docs: http://localhost:8000/docs
- Qdrant Dashboard: http://localhost:6333/dashboard

### Check Logs
All service logs are in Docker compose output

### Common Issues
See TROUBLESHOOTING.md for detailed solutions

## Security Notes

⚠️ **Before deploying to production:**

1. Change JWT_SECRET in `.env`
2. Change default admin password
3. Enable HTTPS
4. Set up proper authentication
5. Configure firewall rules
6. Regular backups

---

**🎉 You're all set! Enjoy using LLM Planner!**
