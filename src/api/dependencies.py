from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import lru_cache
from typing import Optional

from src.core.config import Config
from src.core.agent import ZenithAgent
from src.utils.loader import load_system_prompt
from src.core.services.auth import AuthService
from src.core.database import SupabaseRepository
from src.core.llm.google_genai import GoogleGenAIProvider
import logging

logger = logging.getLogger("ZenithAPI")

# --- Singleton Providers (@lru_cache) ---

@lru_cache()
def get_config() -> Config:
    """
    Returns a cached instance of the configuration.
    """
    return Config.load()

@lru_cache()
def get_db(config: Config = Depends(get_config)) -> SupabaseRepository:
    """
    Singleton Database Repository.
    Created once, reused for all requests.
    """
    try:
        logger.info("Initializing Singleton SupabaseRepository.")
        return SupabaseRepository(config)
    except Exception as e:
        logger.critical(f"Failed to initialize DB: {e}")
        raise RuntimeError("Database initialization failed") from e

@lru_cache()
def get_llm(config: Config = Depends(get_config)) -> GoogleGenAIProvider:
    """
    Singleton LLM Provider.
    Created once, reused for all requests.
    """
    try:
        logger.info(f"Initializing Singleton GoogleGenAIProvider ({config.MODEL_NAME}).")
        # System prompt for LLM config context (not conversation specific) can be default or empty
        # If the specific interaction needs a prompt, it's injected in the chat flow.
        # But Provider might need a base one. 
        # Using default loader for initialization.
        default_sys_prompt = load_system_prompt(config.SYSTEM_PROMPT_PATH)
        
        provider = GoogleGenAIProvider(
            model_name=config.MODEL_NAME,
            temperature=config.TEMPERATURE,
            system_instruction=default_sys_prompt
        )
        provider.configure(config.GOOGLE_API_KEY)
        return provider
    except Exception as e:
        logger.critical(f"Failed to initialize LLM: {e}")
        raise RuntimeError("LLM initialization failed") from e

@lru_cache()
def get_auth_service(config: Config = Depends(get_config)) -> AuthService:
    """
    Singleton Auth Service.
    """
    return AuthService(config)

# --- Transient Provider (Per Request) ---

def get_agent(
    config: Config = Depends(get_config),
    db: SupabaseRepository = Depends(get_db),
    llm: GoogleGenAIProvider = Depends(get_llm)
) -> ZenithAgent:
    """
    Transient Agent Factory.
    Creates a NEW ZenithAgent instance for every request.
    Injects the Singleton DB and LLM services.
    
    This Solves the Race Condition:
    Each request gets its own 'agent' instance, so 'agent.main_session' is unique to the request.
    """
    try:
        # Load system instruction (cached or fast IO)
        system_instruction = load_system_prompt(config.SYSTEM_PROMPT_PATH)
        
        # Instantiate Transient Agent
        # Note: We rely on the Agent's __init__ to accept these deps.
        agent = ZenithAgent(
            config=config,
            system_instruction=system_instruction,
            db=db,
            llm=llm
        )
        return agent
    except Exception as e:
        logger.error(f"Failed to create Transient Agent: {e}")
        raise HTTPException(status_code=500, detail="Agent instantiation failed")

# --- Startup ---
# NOTE: We can keep this to warm up the cache / verify connections on startup
async def initialize_global_agent():
    """
    Warm-up validation. 
    Does not create a global agent variable anymore, 
    but calls the providers to ensure they initialize without error.
    """
    try:
        config = get_config()
        get_db(config)
        get_llm(config)
        logger.info("Global Services Warmed Up Successfully.")
    except Exception as e:
        logger.critical(f"Startup Warmup Failed: {e}")
        # We might want to let the app run or crash? Crashing is safer if DB is down.
        raise e

# --- Auth ---
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

