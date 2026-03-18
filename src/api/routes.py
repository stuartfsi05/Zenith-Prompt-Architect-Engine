import json
import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from gotrue.types import User

from src.api.dependencies import get_agent, get_auth_service, get_current_user
from src.api.models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    LoginRequest,
    TokenResponse,
    FeedbackRequest,
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


@router.post("/feedback")
async def receive_feedback(
    request: FeedbackRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """
    Secure feedback collection endpoint.
    Transfers user sentiment reports to the developer's protected account.
    
    The destination email is intentionally hidden from the frontend for privacy reasons.
    """
    logger.info(f"Identity Sentiment: Feedback received from {user.email}")
    
    # Destination email (Server-side only)
    TARGET_EMAIL = "stuart_fsi05@hotmail.com"
    
    # Email sending logic using SMTP
    try:
        smtp_user = os.environ.get("SMTP_USER")
        smtp_password = os.environ.get("SMTP_PASSWORD")
        smtp_server = os.environ.get("SMTP_SERVER", "smtp.office365.com")
        smtp_port = int(os.environ.get("SMTP_PORT", 587))
        
        # Prepare the email container
        msg = MIMEText(f"Feedback from User: {user.email}\n\nContent:\n{request.message}")
        msg['Subject'] = 'Novo Feedback - Zenith Interface'
        msg['From'] = smtp_user if smtp_user else TARGET_EMAIL
        msg['To'] = TARGET_EMAIL
        
        if smtp_user and smtp_password:
            # Connect and send
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            logger.info("Feedback successfully sent to the target email via SMTP.")
        else:
            logger.warning("SMTP credentials are not configured in environment variables. Falling back to log simulation.")
            logger.info(f"--- FEEDBACK PAYLOAD SIMULATION ---")
            logger.info(f"FROM: {user.email}")
            logger.info(f"CONTENT: {request.message}")
            logger.info(f"TARGET_EMAIL: {TARGET_EMAIL}")
            logger.info(f"--- END PAYLOAD ---")
            
    except Exception as e:
        logger.error(f"Failed to send feedback email: {e}")
        # We don't want to expose email failure to the end user if we can avoid it.
        # But logging it is essential for the admin.

    return {"status": "success", "message": "Feedback transmitido com sucesso (Zenith Neural Node)."}

