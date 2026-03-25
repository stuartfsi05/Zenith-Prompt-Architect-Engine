import json
import logging
import os
import httpx
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from gotrue.types import User

from src.api.dependencies import get_agent, get_auth_service, get_current_user, get_config, get_db
from src.core.config import Config
from src.api.models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    LoginRequest,
    TokenResponse,
    FeedbackRequest,
    RegisterRequest,
)
from src.core.agent import ZenithAgent
from src.core.services.auth import AuthService

# Router configuration for the Zenith Neural Engine API
router = APIRouter()
logger = logging.getLogger("ZenithAPI")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Performs a system health check.

    Returns:
        HealthResponse: Status and version information.
    """
    return HealthResponse(status="ok", version="1.0.0")


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: LoginRequest, auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    """
    Exchanges user credentials for a secure Supabase JWT Access Token.

    Args:
        form_data (LoginRequest): Email and password payload.
        auth_service (AuthService): Injected authentication service.

    Returns:
        TokenResponse: Access token and authorized user metadata.

    Raises:
        HTTPException: If authentication fails (handled by AuthService).
    """
    logger.info(f"Identity Verification: Attempting login for user {form_data.email}")
    session_data = auth_service.login_user(form_data.email, form_data.password)

    # Serialize user metadata for the frontend
    user_obj = session_data.get("user")
    user_info = None
    if user_obj:
        user_info = {
            "id": user_obj.id,
            "email": user_obj.email,
            "role": user_obj.role,
        }

    return TokenResponse(
        access_token=session_data["access_token"],
        token_type=session_data["token_type"],
        user_info=user_info,
    )


@router.post("/register", response_model=TokenResponse)
async def register_new_user(
    form_data: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    """
    Creates a new user account in Supabase using email and password.
    
    Returns an access token if no email confirmation is mandated by the Supabase project configuration.
    """
    logger.info(f"Identity Provisioning: Creating account for user {form_data.email}")
    session_data = auth_service.register_user(form_data.email, form_data.password)

    user_obj = session_data.get("user")
    user_info = None
    if user_obj:
        user_info = {
            "id": user_obj.id,
            "email": user_obj.email,
            "role": user_obj.role,
        }

    return TokenResponse(
        access_token=session_data["access_token"],
        token_type=session_data["token_type"],
        user_info=user_info,
    )


@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    agent: ZenithAgent = Depends(get_agent),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Primary chat interface providing real-time neural streaming responses.

    Requires a valid 'Authorization: Bearer <token>' header.

    Args:
        request (ChatRequest): Message and session context.
        agent (ZenithAgent): Automated orchestrator instance (Transient).
        user (User): The authenticated user entity.

    Returns:
        StreamingResponse: An NDJSON stream of the agent's thought process and response.
    """
    logger.info(
        f"Neural Request: Session {request.session_id} | "
        f"User {user.id} | Prompt: '{request.message[:30]}...'"
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        """Orchestrates the asynchronous streaming pipeline for the response."""
        try:
            # Transfer execution to the Zenith Processing Unit (Agent)
            async for chunk in agent.run_analysis_async(
                user_input=request.message,
                user_id=user.id,
                session_id=request.session_id,
            ):
                response = ChatResponse(content=chunk)
                yield json.dumps(response.model_dump()) + "\n"

        except Exception as e:
            logger.exception(f"Neural Stream Interruption: {e}")
            error_payload = {"error": "Processing unit encountered an internal failure.", "detail": str(e)}
            yield json.dumps(error_payload) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@router.get("/sessions")
async def get_recent_sessions(
    user: User = Depends(get_current_user),
    db = Depends(get_db)
) -> dict:
    """Retrieves the recent chat sessions for the authenticated user."""
    sessions = db.get_sessions(user.id, limit=15)
    return {"status": "success", "sessions": sessions}


@router.post("/feedback")
async def receive_feedback(
    request: FeedbackRequest,
    user: User = Depends(get_current_user),
    config: Config = Depends(get_config),
) -> dict:
    """
    Secure feedback collection endpoint.
    Routes feedback through a Supabase Edge Function to bypass Render's SMTP restrictions.
    Feedback is stored in the Supabase database and optionally emailed to the developer.
    """
    logger.info(f"Identity Sentiment: Feedback received from {user.email}")

    try:
        supabase_url = config.SUPABASE_URL
        supabase_key = config.SUPABASE_KEY.get_secret_value() if config.SUPABASE_KEY else None

        if not supabase_url or not supabase_key:
            logger.error("Supabase credentials not configured. Cannot relay feedback.")
            raise HTTPException(
                status_code=500,
                detail="Configuração do serviço de feedback ausente."
            )

        edge_function_url = f"{supabase_url}/functions/v1/send-feedback"

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                edge_function_url,
                json={
                    "user_email": user.email,
                    "message": request.message,
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {supabase_key}",
                },
            )

        if response.status_code != 200:
            logger.error(f"Edge Function returned {response.status_code}: {response.text}")
            raise HTTPException(
                status_code=500,
                detail="Erro ao processar o feedback. Tente novamente mais tarde."
            )

        result = response.json()
        logger.info(f"Feedback relay result: stored={result.get('stored_in_db')}, emailed={result.get('email_sent')}")

        return {"status": "success", "message": "Feedback transmitido com sucesso (Zenith Neural Node)."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to relay feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao enviar o feedback. Por favor, tente novamente mais tarde."
        )
