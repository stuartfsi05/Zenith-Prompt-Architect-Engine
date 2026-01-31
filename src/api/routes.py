from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from src.api.models import ChatRequest, ChatResponse, HealthResponse
from src.api.dependencies import get_agent, get_current_user
from src.core.agent import ZenithAgent
from gotrue.types import User
import json
import logging

router = APIRouter()
logger = logging.getLogger("ZenithAPI")

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", version="1.0.0")

@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest, 
    agent: ZenithAgent = Depends(get_agent),
    user: User = Depends(get_current_user)
):
    """
    Chat endpoint that accepts a message and returns a streaming response.
    Requires a valid JWT token.
    """
    logger.info(f"Received chat request for session {request.session_id} from user {user.id}")
    
    async def event_generator():
        try:
            # Execute agent analysis stream with user context
            async for chunk in agent.run_analysis_async(request.message, user_id=user.id, session_id=request.session_id):
                response = ChatResponse(content=chunk)
                yield json.dumps(response.model_dump()) + "\n"
        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
