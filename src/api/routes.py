import asyncio
import json
import logging
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from gotrue.types import User

from src.api.dependencies import (
    RequestLLMContext,
    get_agent,
    get_auth_service,
    get_config,
    get_current_user,
    get_llm_context,
    get_quota_service,
    get_user_db,
)
from src.api.models import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    HealthResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from src.core.agent import ZenithAgent
from src.core.config import Config
from src.core.services.auth import AuthService
from src.core.services.quota import DemoQuotaService, QuotaExceededError

router = APIRouter()
logger = logging.getLogger("ZenithAPI")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Performs a system health check."""
    return HealthResponse(status="ok", version="1.0.0")


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: LoginRequest, auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    """Exchanges user credentials for a Supabase JWT Access Token."""
    logger.info(f"Identity Verification: Attempting login for user {form_data.email}")
    session_data = await asyncio.to_thread(
        auth_service.login_user, form_data.email, form_data.password
    )

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
    """Creates a new user account in Supabase using email and password."""
    logger.info(f"Identity Provisioning: Creating account for user {form_data.email}")
    session_data = await asyncio.to_thread(
        auth_service.register_user, form_data.email, form_data.password
    )

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


@router.get("/quota")
async def get_quota_status(
    user: User = Depends(get_current_user),
    config: Config = Depends(get_config),
    llm_ctx: RequestLLMContext = Depends(get_llm_context),
    quota_service: DemoQuotaService = Depends(get_quota_service),
    db=Depends(get_user_db),
) -> dict:
    """Returns active execution mode, model name, and remaining daily Demo quota."""
    remaining = (
        None
        if llm_ctx.mode == "byok"
        else await asyncio.to_thread(quota_service.get_remaining, user.id, db)
    )
    return {
        "mode": llm_ctx.mode,
        "model": llm_ctx.primary_model,
        "daily_limit": config.DEMO_DAILY_LIMIT,
        "remaining": remaining,
    }


@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    agent: ZenithAgent = Depends(get_agent),
    user: User = Depends(get_current_user),
    quota_service: DemoQuotaService = Depends(get_quota_service),
    db=Depends(get_user_db),
) -> StreamingResponse:
    """
    Primary chat interface providing real-time NDJSON streaming responses.
    Enforces daily Demo quota when no BYOK header is provided.
    """
    if agent.mode == "demo":
        try:
            remaining = await asyncio.to_thread(
                quota_service.check_and_consume, user.id, db
            )
            agent.remaining_quota = remaining
        except QuotaExceededError as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Você atingiu o limite diário gratuito de {e.limit} mensagens no Modo Demo. "
                    "Adicione sua Google API Key gratuita (AI Studio) no menu lateral para uso "
                    "ilimitado com Gemini 3.8 Flash!"
                ),
            )

    logger.info(
        f"Neural Request: Session {request.session_id} | "
        f"User {user.id} | Mode {agent.mode} | Prompt: '{request.message[:30]}...'"
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        """Orchestrates the asynchronous streaming pipeline for the response."""
        try:
            async for event in agent.run_analysis_async(
                user_input=request.message,
                user_id=user.id,
                session_id=request.session_id,
            ):
                response = ChatResponse(**event)
                yield json.dumps(response.model_dump()) + "\n"

        except Exception as e:
            logger.exception(f"Neural Stream Interruption: {e}")
            error_payload = {
                "type": "error",
                "error": "Processing unit encountered an internal failure.",
                "detail": str(e),
            }
            yield json.dumps(error_payload) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@router.get("/sessions")
async def get_recent_sessions(
    user: User = Depends(get_current_user), db=Depends(get_user_db)
) -> dict:
    """Retrieves the recent chat sessions for the authenticated user."""
    sessions = await asyncio.to_thread(db.get_sessions, user.id, 15)
    return {"status": "success", "sessions": sessions}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db=Depends(get_user_db),
) -> dict:
    """Retrieves messages for a session owned by the authenticated user."""
    messages = await asyncio.to_thread(db.get_history, session_id, user.id)
    return {"status": "success", "session_id": session_id, "messages": messages}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db=Depends(get_user_db),
) -> dict:
    """Deletes a chat session and its interactions after ownership check."""
    deleted = await asyncio.to_thread(db.delete_session, session_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    return {"status": "success", "session_id": session_id}


@router.post("/feedback")
async def receive_feedback(
    request: FeedbackRequest,
    user: User = Depends(get_current_user),
    config: Config = Depends(get_config),
) -> dict:
    """
    Secure feedback collection endpoint via Supabase Edge Function.
    """
    logger.info(f"Identity Sentiment: Feedback received from {user.email}")

    try:
        supabase_url = config.SUPABASE_URL
        supabase_key = (
            config.SUPABASE_KEY.get_secret_value() if config.SUPABASE_KEY else None
        )

        if not supabase_url or not supabase_key:
            logger.error("Supabase credentials not configured. Cannot relay feedback.")
            raise HTTPException(
                status_code=500, detail="Configuração do serviço de feedback ausente."
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
            logger.error(
                f"Edge Function returned {response.status_code}: {response.text}"
            )
            raise HTTPException(
                status_code=500,
                detail="Erro ao processar o feedback. Tente novamente mais tarde.",
            )

        result = response.json()
        logger.info(
            f"Feedback relay result: stored={result.get('stored_in_db')}, emailed={result.get('email_sent')}"
        )

        return {
            "status": "success",
            "message": "Feedback transmitido com sucesso (Zenith Neural Node).",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to relay feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao enviar o feedback. Por favor, tente novamente mais tarde.",
        )
