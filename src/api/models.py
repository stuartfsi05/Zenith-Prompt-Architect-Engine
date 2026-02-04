from pydantic import BaseModel, Field
from typing import Optional, List, Any

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's message to the agent")
    session_id: str = Field(default="default_session", description="Session identifier for conversation history")

class ChatResponse(BaseModel):
    """
    Standard response model. 
    For streaming, this schema might not strictly apply to the chunked output,
    but represents the logical structure of a message part.
    """
    content: str = Field(..., description="The chunk or full content of the response")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Additional metadata (e.g., retrieval sources, scores)")

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
