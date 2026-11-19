from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=12000,
        description="The user's message to the agent",
    )
    session_id: str = Field(
        default="default_session",
        description="Session identifier for conversation history",
    )


class ChatResponse(BaseModel):
    """
    Typed streaming event emitted over NDJSON ('meta', 'chunk', 'quality', or 'error').
    """

    type: str = Field(default="chunk", description="Event type")
    content: str = Field(default="", description="The chunk or message content")
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional metadata (e.g., quota, mode, quality evaluation)",
    )


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email for authentication in Supabase")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_info: Optional[dict] = Field(None, description="Basic user information")


class FeedbackRequest(BaseModel):
    message: str = Field(
        ..., min_length=1, max_length=2000, description="The feedback content"
    )


class RegisterRequest(BaseModel):
    email: str = Field(..., description="New user email")
    password: str = Field(..., description="New user password (should be strong)")
