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
    
    # Update agent's database manager context?
    # The agent instance is global, BUT it uses `self.db` which is global.
    # We need to tell the agent WHO is talking so it logs correctly.
    # Refactoring ZenithAgent to accept user_id in run_analysis_async might be cleaner,
    # OR we handle the session setup here and the agent just "runs".
    # BUT the agent calculates memory and history.
    
    # OPTION: Pass user_id to run_analysis_async
    # We need to modify ZenithAgent.run_analysis_async to accept user_id and pass it to db.
    
    # For now, let's assume we modified ZenithAgent to take user_id in run_analysis_async
    # OR we monkey-patch/set context on the agent? No, that's not thread safe.
    
    # We must modify ZenithAgent signature. 
    # Let's do that in a separate step or assume I did it? 
    # I haven't done it yet. I need to modify ZenithAgent too.
    
    # Let's update this route assuming the method signature update comes next.
    
    async def event_generator():
        try:
            # Passing user_id to agent
            async for chunk in agent.run_analysis_async(request.message, user_id=user.id, session_id=request.session_id):
                response = ChatResponse(content=chunk)
                yield json.dumps(response.model_dump()) + "\n"
        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
