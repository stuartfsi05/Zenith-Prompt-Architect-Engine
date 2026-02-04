from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from src.api.models import ChatRequest, ChatResponse, HealthResponse, LoginRequest, TokenResponse
from src.api.dependencies import get_agent, get_current_user, get_auth_service
from src.core.agent import ZenithAgent
from src.core.services.auth import AuthService
from gotrue.types import User
import json
import logging

router = APIRouter()
logger = logging.getLogger("ZenithAPI")

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", version="1.0.0")

@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Exchanges user credentials (email/password) for a Supabase JWT Access Token.
    """
    logger.info(f"Token generation request for: {form_data.email}")
    session_data = auth_service.login_user(form_data.email, form_data.password)
    
    # Extract user info safely
    user = session_data.get("user")
    user_info = None
    if user:
         user_info = {
             "id": user.id,
             "email": user.email,
             "role": user.role
         }

    return TokenResponse(
        access_token=session_data["access_token"],
        token_type=session_data["token_type"],
        user_info=user_info
    )

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
