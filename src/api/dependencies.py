from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.core.config import Config
from src.core.agent import ZenithAgent
from src.utils.loader import load_system_prompt
from src.core.services.auth import AuthService
import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger("ZenithAPI")

# Global instance to hold the agent after startup
_agent_instance: Optional[ZenithAgent] = None

@lru_cache()
def get_config() -> Config:
    """
    Returns a cached instance of the configuration.
    """
    return Config.load()

@lru_cache()
def get_auth_service() -> AuthService:
    """
    Returns a cached instance of the AuthService.
    """
    return AuthService(get_config())

def get_agent() -> ZenithAgent:
    """
    Dependency to get the initialized ZenithAgent instance.
    Raises an error if the agent hasn't been initialized via the startup event.
    """
    global _agent_instance
    if _agent_instance is None:
        raise RuntimeError("ZenithAgent is not initialized. Ensure startup event ran.")
    return _agent_instance

async def initialize_global_agent():
    """
    Initializes the global ZenithAgent instance.
    Should be called during application startup.
    """
    global _agent_instance
    config = get_config()
    
    try:
        system_instruction = load_system_prompt(config.SYSTEM_PROMPT_PATH)
        _agent_instance = ZenithAgent(config, system_instruction)
        # Check if we need to start a session explicitly or if it's per request
        # For now, let's just initialize it. 
        # Ideally, start_chat is per-session, but ZenithAgent structure implies one active session in 'main_session'
        # We might need to adapt ZenithAgent for multi-session if the API supports it in the future.
        # For this refactor, we'll stick to a default session or handle it in the route.
        # We start with a system session. The database manager creates it if not exists.
        _agent_instance.start_chat(session_id="api_system_session", user_id="system_init")
        logger.info("Global ZenithAgent initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize ZenithAgent: {e}")
        raise e

# Auth
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Verifies the JWT token using Supabase Auth via AuthService.
    Returns the user object if valid.
    """
    token = credentials.credentials
    return auth_service.verify_token(token)
