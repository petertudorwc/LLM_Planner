# Project Architecture

This document provides a detailed overview of the LLM Planner system architecture.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│                      http://localhost:3000                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Chat View   │  │   Map View   │  │ Upload View  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP/WebSocket
┌─────────────────────────────▼───────────────────────────────────┐
│                    API Gateway (FastAPI)                        │
│                      http://localhost:8000                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │   Auth   │  │   Chat   │  │ Mapping  │  │ Ingestion│      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
└───────┬────────┬────────┬────────┬────────┬────────┬───────────┘
        │        │        │        │        │        │
        │        │        │        │        │        │
┌───────▼────┐ ┌▼────────▼─┐ ┌───▼────┐ ┌─▼──────┐ ┌▼──────────┐
│    LLM     │ │  Vector   │ │Mapping │ │Embedding││ Ingestion  │
│  Service   │ │   Store   │ │Service │ │Service  ││  Service   │
│  (Ollama)  │ │ (Qdrant)  │ │(PostGIS│ │(ST)     ││  (Docs)    │
│   :8001    │ │   :6333   │ │ :8003  │ │  :8002  ││   :8005    │
└────────────┘ └───────────┘ └────────┘ └─────────┘ └───────────┘
     │                                                      │
     │                                              ┌───────▼──────┐
     │                                              │    Speech    │
     │                                              │   Service    │
     │                                              │  (Whisper)   │
     │                                              │    :8004     │
     └──────────────────────────────────────────────┴──────────────┘
```

## Service Details

### 1. Frontend (React + Material-UI)
**Port:** 3000  
**Purpose:** User interface

**Components:**
- `LoginPage`: Authentication screen
- `MainLayout`: Main application shell with navigation
- `ChatPanel`: Conversational interface with voice input
- `MapView`: Interactive Leaflet map with layers
- `UploadPanel`: File upload and processing interface

**Key Features:**
- JWT authentication
- Real-time WebSocket communication
- Voice recording and transcription
- Interactive map with GeoJSON layers
- File upload with progress tracking

### 2. API Gateway (FastAPI)
**Port:** 8000  
**Purpose:** Central orchestrator and request router

**Routers:**
- `/api/auth`: Authentication (login, logout, user info)
- `/api/chat`: Chat message handling and LLM coordination
- `/api/mapping`: Map layer management
- `/api/ingest`: Document upload and processing
- `/api/speech`: Audio transcription

**Key Features:**
- JWT token validation
- CORS middleware
- WebSocket support
- Service coordination
- Error handling and logging

### 3. LLM Service (Ollama + FastAPI Wrapper)
**Port:** 8001  
**Model:** Qwen3 8B (POC) / Qwen3 32B or Llama 3.3 70B (Production)

**Capabilities:**
- Natural language understanding
- Advanced function calling for tool use
- Thinking mode for complex reasoning
- Context-aware conversations
- Structured output generation

**Function Definitions:**
- `search_knowledge`: Query vector database
- `map_plot_points`: Plot points on map
- `map_draw_polygon`: Draw regions on map

### 4. Embedding Service (sentence-transformers)
**Port:** 8002  
**Model:** all-mpnet-base-v2 (768 dimensions)

**Endpoints:**
- `/embed`: Generate embeddings for text
- `/similarity`: Compute cosine similarity

**Features:**
- Fast CPU/GPU inference
- Batch processing
- Normalized embeddings

### 5. Vector Store (Qdrant)
**Port:** 6333 (REST), 6334 (gRPC)  
**Purpose:** Semantic search over documents

**Collections:**
- `documents`: Main document collection

**Features:**
- Cosine similarity search
- Metadata filtering
- Persistent storage
- Web dashboard at :6333/dashboard

### 6. Mapping Service (FastAPI + PostGIS)
**Port:** 8003  
**Database:** PostgreSQL with PostGIS extension

**Endpoints:**
- `/layers`: CRUD operations for map layers
- `/tiles/{layer}/{z}/{x}/{y}.png`: Tile serving
- `/execute`: Function execution from LLM

**Features:**
- GeoJSON support
- Spatial queries
- Layer management
- Offline tile caching

### 7. Data Ingestion Service (FastAPI)
**Port:** 8005  
**Purpose:** Process and index documents

**Supported Formats:**
- PDF (pypdf)
- Word (python-docx)
- Excel (openpyxl)
- CSV (pandas)
- GeoJSON, Shapefile, KML

**Processing Pipeline:**
1. File upload via API Gateway
2. Format detection
3. Text extraction and chunking
4. Embedding generation
5. Vector storage
6. Geospatial data to mapping service

### 8. Speech Recognition Service (Whisper)
**Port:** 8004  
**Model:** Whisper base (POC) / medium (Production)

**Endpoints:**
- `/transcribe`: Audio to text conversion
- `/models`: List available models

**Features:**
- Multiple audio formats
- Automatic language detection
- Offline operation

### 9. Database Services

#### PostGIS
**Port:** 5432  
**Purpose:** Spatial database for mapping

**Schema:**
- `map_layers`: Stores layer geometries and properties

#### Qdrant
**Port:** 6333  
**Purpose:** Vector database

**Collections:**
- `documents`: 768-dim vectors + metadata

## Data Flow

### Chat Query Flow

```
User Input
    ↓
Frontend (Speech → Text)
    ↓
API Gateway (/api/chat/message)
    ↓
Vector Store Search (relevant context)
    ↓
LLM Service (generate response + function calls)
    ↓
Function Execution (if needed)
    │
    ├→ Mapping Service (plot data)
    └→ Vector Store (search more)
    ↓
API Gateway (aggregate response)
    ↓
Frontend (display + update map)
```

### Document Upload Flow

```
User Upload
    ↓
Frontend (FormData)
    ↓
API Gateway (/api/ingest/upload)
    ↓
Ingestion Service
    │
    ├→ Format Detection
    ├→ Text Extraction
    ├→ Chunking
    ↓
Embedding Service (/embed)
    ↓
Vector Store (store vectors)
    ↓
Success Response
```

## Technology Stack

### Backend
- **Python 3.11**: Main language
- **FastAPI**: Web framework
- **Uvicorn**: ASGI server
- **Ollama**: LLM serving
- **Qdrant**: Vector database
- **PostGIS**: Spatial database

### Frontend
- **React 18**: UI framework
- **Material-UI**: Component library
- **Leaflet**: Map library
- **Axios**: HTTP client

### AI/ML
- **Qwen3**: Language model (newer, better function calling)
- **Whisper**: Speech recognition
- **sentence-transformers**: Embeddings

### DevOps
- **Docker**: Containerization
- **Docker Compose**: Orchestration
- **NVIDIA Docker**: GPU support

## Networking

### Internal Network (llm_planner_network)

All services communicate via Docker's internal network:

```
api-gateway → llm-service:8001
api-gateway → vector-store:6333
api-gateway → embedding-service:8002
api-gateway → mapping-service:8003
api-gateway → speech-service:8004
api-gateway → ingestion-service:8005

ingestion-service → embedding-service:8002
ingestion-service → vector-store:6333
ingestion-service → mapping-service:8003

mapping-service → postgis:5432
```

### External Ports

```
3000  → Frontend
8000  → API Gateway
6333  → Qdrant Dashboard (optional)
```

## Security

### Authentication
- JWT tokens with configurable expiry
- HTTP Bearer authentication
- In-memory user store (POC)
- TODO: Database-backed users, RBAC

### Network Security
- Internal Docker network isolation
- CORS protection
- Rate limiting (TODO)
- HTTPS (TODO for production)

### Data Security
- No data leaves the system (offline-capable)
- Encrypted JWT tokens
- Secure password hashing (bcrypt)

## Scalability

### Horizontal Scaling
- **API Gateway**: Load balancer ready
- **LLM Service**: Multiple instances with queue
- **Embedding Service**: Stateless, easily replicated
- **Mapping/Speech/Ingestion**: Stateless services

### Vertical Scaling
- **LLM**: Larger models (Qwen3 32B, Llama 3.3 70B+) with more RAM/GPU
- **Vector Store**: Qdrant clustering
- **PostGIS**: PostgreSQL replication

### Optimization Points
- Redis cache for frequent queries
- CDN for tile serving
- Model quantization for faster inference
- Connection pooling
- Async processing queues

## Monitoring

### Health Checks
Each service exposes `/health` endpoint:
- Service status
- Model loaded state
- Database connectivity

### Logging
- Structured logging with timestamps
- Service-specific log levels
- Docker log aggregation

### Metrics (TODO)
- Request latency
- Token usage
- Error rates
- Resource utilization

## Development

### Adding New Services

1. Create service directory
2. Write Dockerfile
3. Add to docker-compose.yml
4. Update API Gateway routes
5. Document endpoints

### Debugging

**View all logs:**
```bash
docker-compose logs -f
```

**Single service:**
```bash
docker-compose logs -f llm-service
```

**Exec into container:**
```bash
docker-compose exec api-gateway /bin/bash
```

## Production Considerations

### Before Deployment

1. ✅ Change JWT_SECRET
2. ✅ Update default credentials
3. ✅ Enable HTTPS
4. ✅ Set up proper authentication
5. ✅ Configure firewalls
6. ✅ Set up backups
7. ✅ Monitor resource usage
8. ✅ Add rate limiting
9. ✅ Set up logging aggregation
10. ✅ Document operational procedures

### Hardware Requirements

**Minimum (POC):**
- GPU: RTX 3080 (10GB VRAM)
- RAM: 32GB
- Storage: 100GB SSD

**Recommended (Production):**
- GPU: RTX 4090 / AMD Ryzen AI Max
- RAM: 64GB+
- Storage: 500GB NVMe SSD
- Network: 1Gbps

---

**Version:** 1.0.0-POC  
**Last Updated:** November 2025  
**Authors:** LLM Planner Team
