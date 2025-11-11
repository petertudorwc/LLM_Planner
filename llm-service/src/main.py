from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import logging
import os
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LLM Service",
    description="Ollama-based language model service with function calling",
    version="1.0.0"
)

OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.1:8b")

# Define available functions for the LLM
AVAILABLE_FUNCTIONS = {
    "search_knowledge": {
        "name": "search_knowledge",
        "description": "Search the knowledge base for relevant information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "limit": {"type": "integer", "description": "Number of results to return", "default": 5}
            },
            "required": ["query"]
        }
    },
    "map_plot_points": {
        "name": "map_plot_points",
        "description": "Plot points on the map",
        "parameters": {
            "type": "object",
            "properties": {
                "points": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "lat": {"type": "number"},
                            "lon": {"type": "number"},
                            "label": {"type": "string"},
                            "properties": {"type": "object"}
                        }
                    }
                },
                "layer_name": {"type": "string", "description": "Name of the layer to create"}
            },
            "required": ["points"]
        }
    },
    "map_draw_polygon": {
        "name": "map_draw_polygon",
        "description": "Draw a polygon or region on the map",
        "parameters": {
            "type": "object",
            "properties": {
                "coordinates": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"}
                    }
                },
                "style": {"type": "object", "properties": {"color": {"type": "string"}, "fillOpacity": {"type": "number"}}}
            },
            "required": ["coordinates"]
        }
    },
    "map_delete_layer": {
        "name": "map_delete_layer",
        "description": "Delete a map layer by its ID. Common layer IDs: 'llm_polygon' for polygons, 'llm_points' for points",
        "parameters": {
            "type": "object",
            "properties": {
                "layer_id": {"type": "string", "description": "The ID of the layer to delete"}
            },
            "required": ["layer_id"]
        }
    },
    "geocode_place": {
        "name": "geocode_place",
        "description": "Look up coordinates for any UK place name (city, town, village). Returns latitude and longitude.",
        "parameters": {
            "type": "object",
            "properties": {
                "place_name": {"type": "string", "description": "Name of the place to look up"},
                "limit": {"type": "integer", "description": "Maximum results (default 5)", "default": 5}
            },
            "required": ["place_name"]
        }
    }
}

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []
    use_functions: bool = True

class ChatResponse(BaseModel):
    response: str
    function_call: Optional[Dict[str, Any]] = None
    function_calls: Optional[List[Dict[str, Any]]] = None
    model: str

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "LLM Service",
        "model": MODEL_NAME,
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
            if response.status_code == 200:
                return {"status": "healthy", "ollama": "connected", "model": MODEL_NAME}
    except:
        pass
    return {"status": "unhealthy", "ollama": "disconnected"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the LLM"""
    try:
        # Build prompt with function definitions if enabled
        system_prompt = """You are an AI assistant helping with disaster relief planning and data visualization.

You have access to a comprehensive UK places database via the geocode_place function.
For any UK town, city, or village, use geocode_place to look up coordinates.

Pre-loaded major cities (use these directly without geocoding):
- London: 51.5074°N, -0.1278°W
- Manchester: 53.4808°N, -2.2426°W
- Birmingham: 52.4862°N, -1.8904°W
- Oxford: 51.7520°N, -1.2577°W
- Abingdon: 51.6708°N, -1.2837°W

For circular boundaries around a point:
- 1 mile ≈ 0.0145° latitude, 0.0182° longitude (at UK latitudes)
- 2 miles ≈ 0.029° latitude, 0.0364° longitude
- 5 miles ≈ 0.0725° latitude, 0.091° longitude
- Calculate 12-16 points in a circle using these approximations

CRITICAL INSTRUCTION: When the user asks you to "draw", "plot", "show", "create a boundary", or any similar action:
1. Calculate the coordinates if needed
2. ALWAYS call the appropriate function (map_plot_points or map_draw_polygon)
3. Do NOT just explain what you would do - ACTUALLY DO IT with a FUNCTION_CALL

When you need to execute an action, respond with a JSON function call in this exact format:
FUNCTION_CALL: {"name": "function_name", "parameters": {...}}

You can make multiple function calls by repeating FUNCTION_CALL: for each action.

Available functions:

1. geocode_place - Look up any UK place coordinates (only use for unknown places)
   Parameters: {"place_name": "Abingdon", "limit": 1}
   Returns: Automatically plots the place on the map

2. search_knowledge - Search the knowledge base
   Parameters: {"query": "search text", "limit": 5}

3. map_plot_points - Plot points on the map (use when you already have coordinates)
   Parameters: {"points": [{"lat": 51.5074, "lon": -0.1278, "label": "Label"}], "layer_name": "Optional descriptive name"}
   Note: The system automatically generates unique IDs for each layer, so you can plot multiple point sets without conflict.

4. map_draw_polygon - Draw polygon on map
   Parameters: {"coordinates": [[lon, lat], [lon, lat], ...], "style": {"color": "red", "fillOpacity": 0.3}}
   CRITICAL: The polygon MUST be closed - the last coordinate MUST be identical to the first coordinate!
   Example: [[-1.32, 51.67], [-1.31, 51.69], [-1.26, 51.67], [-1.32, 51.67]] ← Notice first and last are the same!
   Note: Each polygon gets a unique ID automatically. You can draw multiple polygons without them replacing each other.

5. map_delete_layer - Delete a layer from the map
   Parameters: {"layer_id": "polygon_20231111_143022_123"}
   Note: Use the exact layer ID from the Layers tab. Each shape has a unique timestamped ID.

Examples:
- Plot unknown places: FUNCTION_CALL: {"name": "geocode_place", "parameters": {"place_name": "Small Town", "limit": 1}}
- Plot multiple known places:
  FUNCTION_CALL: {"name": "map_plot_points", "parameters": {"points": [{"lat": 51.6708, "lon": -1.2837, "label": "Abingdon"}, {"lat": 51.7520, "lon": -1.2577, "label": "Oxford"}]}}
- Draw 2-mile circle around Abingdon (51.6708, -1.2837):
  FUNCTION_CALL: {"name": "map_draw_polygon", "parameters": {"coordinates": [[-1.3201, 51.6998], [-1.3019, 51.7054], [-1.2811, 51.7054], [-1.2629, 51.6998], [-1.2511, 51.6854], [-1.2473, 51.6708], [-1.2511, 51.6562], [-1.2629, 51.6418], [-1.2811, 51.6362], [-1.3019, 51.6362], [-1.3201, 51.6418], [-1.3319, 51.6562], [-1.3357, 51.6708], [-1.3319, 51.6854], [-1.3201, 51.6998]], "style": {"color": "blue", "fillOpacity": 0.2}}}

Always include FUNCTION_CALL: when you want to execute an action."""
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        for msg in request.history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": request.message})
        
        # Call Ollama
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODEL_NAME,
                    "messages": messages,
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Ollama API error")
            
            result = response.json()
            assistant_message = result.get("message", {}).get("content", "")
        
        # Parse for function calls with FUNCTION_CALL: prefix
        function_calls = []
        if "FUNCTION_CALL:" in assistant_message:
            try:
                # Extract all FUNCTION_CALL: occurrences
                parts = assistant_message.split("FUNCTION_CALL:")
                for part in parts[1:]:  # Skip first part (text before first FUNCTION_CALL)
                    json_str = part.strip()
                    # Find the JSON object
                    brace_start = json_str.find("{")
                    if brace_start != -1:
                        # Simple brace matching
                        count = 0
                        end = brace_start
                        for i, char in enumerate(json_str[brace_start:], start=brace_start):
                            if char == "{":
                                count += 1
                            elif char == "}":
                                count -= 1
                                if count == 0:
                                    end = i + 1
                                    break
                        json_str = json_str[brace_start:end]
                        func_call = json.loads(json_str)
                        function_calls.append(func_call)
                        logger.info(f"Parsed function call: {func_call}")
            except Exception as e:
                logger.error(f"Error parsing function calls: {e}")
        
        # Return first function call for compatibility (API gateway will need update for multiple)
        function_call = function_calls[0] if function_calls else None
        
        logger.info(f"LLM responded to query: {request.message[:50]}...")
        
        return {
            "response": assistant_message,
            "function_call": function_call,
            "function_calls": function_calls if len(function_calls) > 1 else None,
            "model": MODEL_NAME
        }
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="LLM request timeout")
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_models():
    """List available models"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags", timeout=10.0)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
