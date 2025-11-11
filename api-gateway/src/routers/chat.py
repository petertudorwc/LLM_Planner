from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import httpx
import logging

from ..core.security import get_current_user
from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[ChatMessage] = []

class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[dict]] = None
    map_updates: Optional[List[dict]] = None

@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send message to LLM and get response"""
    try:
        # Step 1: Search vector store for relevant context
        async with httpx.AsyncClient() as client:
            # Query vector store
            vector_response = await client.post(
                f"{settings.VECTOR_STORE_URL}/collections/documents/points/search",
                json={
                    "query": request.message,
                    "limit": 5
                },
                timeout=30.0
            )
            
            context_documents = []
            if vector_response.status_code == 200:
                context_documents = vector_response.json().get("result", [])
        
        # Step 2: Build prompt with context
        context_text = ""
        if context_documents:
            context_text = "\n\nRelevant context:\n"
            for doc in context_documents:
                context_text += f"- {doc.get('payload', {}).get('text', '')}\n"
        
        # Step 3: Send to LLM
        async with httpx.AsyncClient() as client:
            llm_response = await client.post(
                f"{settings.LLM_SERVICE_URL}/chat",
                json={
                    "message": request.message + context_text,
                    "history": [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]
                },
                timeout=120.0
            )
            
            if llm_response.status_code != 200:
                raise HTTPException(status_code=500, detail="LLM service error")
            
            llm_data = llm_response.json()
        
        # Step 4: Process any function calls (e.g., map updates, geocoding)
        map_updates = []
        
        # Get all function calls (support both single and multiple)
        all_function_calls = []
        if llm_data.get("function_calls"):
            all_function_calls = llm_data["function_calls"]
        elif llm_data.get("function_call"):
            all_function_calls = [llm_data["function_call"]]
        
        # Process each function call
        for function_call in all_function_calls:
            func_name = function_call["name"]
            
            # Handle geocoding
            if func_name == "geocode_place":
                async with httpx.AsyncClient() as client:
                    place_name = function_call["parameters"]["place_name"]
                    limit = function_call["parameters"].get("limit", 5)
                    
                    geocode_response = await client.get(
                        f"{settings.GEOCODING_SERVICE_URL}/search",
                        params={"q": place_name, "limit": limit},
                        timeout=30.0
                    )
                    
                    if geocode_response.status_code == 200:
                        # Get geocoding results
                        places = geocode_response.json().get("places", [])
                        if places:
                            # Automatically plot the geocoded place(s) on the map
                            points = []
                            for place in places[:limit]:  # Plot all results up to limit
                                points.append({
                                    "lat": place["latitude"],
                                    "lon": place["longitude"],
                                    "label": place["name"],
                                    "properties": {
                                        "population": place.get("population", 0),
                                        "feature_code": place.get("feature_code", "")
                                    }
                                })
                            
                            # Create map function call to plot the points
                            map_function_call = {
                                "name": "map_plot_points",
                                "parameters": {
                                    "points": points,
                                    "layer_name": f"geocoded_{place_name.lower().replace(' ', '_')}"
                                }
                            }
                            
                            # Execute the map plot
                            map_response = await client.post(
                                f"{settings.MAPPING_SERVICE_URL}/execute",
                                json=map_function_call,
                                timeout=30.0
                            )
                            
                            if map_response.status_code == 200:
                                map_updates.append(map_response.json())
                                logger.info(f"Geocoded and plotted '{place_name}' at {points[0]['lat']}, {points[0]['lon']}")
            
            # Handle map-related function calls
            elif func_name.startswith("map_"):
                async with httpx.AsyncClient() as client:
                    map_response = await client.post(
                        f"{settings.MAPPING_SERVICE_URL}/execute",
                        json=function_call,
                        timeout=30.0
                    )
                    if map_response.status_code == 200:
                        map_updates.append(map_response.json())
        
        logger.info(f"User {current_user['username']} sent message, received response")
        
        return {
            "response": llm_data.get("response", ""),
            "sources": [{"text": doc.get("payload", {}).get("text", ""), "score": doc.get("score", 0)} for doc in context_documents],
            "map_updates": map_updates
        }
        
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_chat_history(current_user: dict = Depends(get_current_user)):
    """Get chat history for current user"""
    # TODO: Implement chat history storage and retrieval
    return {"history": []}
