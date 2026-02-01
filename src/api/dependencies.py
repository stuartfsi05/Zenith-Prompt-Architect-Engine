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
from src.core.knowledge.manager import StrategicKnowledgeBase
from src.core.context_builder import ContextBuilder
from src.core.analyzer import StrategicAnalyzer
from src.core.judge import TheJudge
from src.core.memory import StrategicMemory
from src.core.validator import SemanticValidator
import logging

logger = logging.getLogger("ZenithAPI")

# --- Singleton Providers (@lru_cache) ---



# ... existing imports ...

# --- Singleton Providers (@lru_cache) ---

@lru_cache()
def get_config() -> Config:
    """
    Returns a cached instance of the configuration.
    """
    return Config()

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
        # Load default system prompt for provider initialization
        default_sys_prompt = load_system_prompt(config.SYSTEM_PROMPT_PATH)
        
        provider = GoogleGenAIProvider(
            model_name=config.MODEL_NAME,
            temperature=config.TEMPERATURE,
            system_instruction=default_sys_prompt
        )
        provider.configure(config.GOOGLE_API_KEY.get_secret_value())
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

@lru_cache()
def get_knowledge_base(config: Config = Depends(get_config)) -> StrategicKnowledgeBase:
    return StrategicKnowledgeBase(config)

@lru_cache()
def get_context_builder() -> ContextBuilder:
    return ContextBuilder()

@lru_cache()
def get_analyzer(config: Config = Depends(get_config)) -> StrategicAnalyzer:
    return StrategicAnalyzer(config)

@lru_cache()
def get_judge(config: Config = Depends(get_config)) -> TheJudge:
    return TheJudge(config)

@lru_cache()
def get_memory(config: Config = Depends(get_config)) -> StrategicMemory:
    return StrategicMemory(config)

@lru_cache()
def get_validator() -> SemanticValidator:
    """
    Singleton Validator.
    Helps prevents future bottlenecks if validation becomes heavy (e.g., BERT models).
    """
    return SemanticValidator()


# --- Transient Provider (Per Request) ---

def get_agent(
    config: Config = Depends(get_config),
    db: SupabaseRepository = Depends(get_db),
    llm: GoogleGenAIProvider = Depends(get_llm),
    knowledge_base: StrategicKnowledgeBase = Depends(get_knowledge_base),
    context_builder: ContextBuilder = Depends(get_context_builder),
    analyzer: StrategicAnalyzer = Depends(get_analyzer),
    judge: TheJudge = Depends(get_judge),
    memory: StrategicMemory = Depends(get_memory),
    validator: SemanticValidator = Depends(get_validator)
) -> ZenithAgent:
    """
    Transient Agent Factory.
    Creates a NEW ZenithAgent instance for every request.
    Injects the Singleton services.
    
    Ensures request isolation and prevents race conditions.
    """
    try:
        # Load system instruction (cached or fast IO)
        system_instruction = load_system_prompt(config.SYSTEM_PROMPT_PATH)
        
        # Instantiate Transient Agent
        agent = ZenithAgent(
            config=config,
            system_instruction=system_instruction,
            db=db,
            llm=llm,
            knowledge_base=knowledge_base,
            context_builder=context_builder,
            analyzer=analyzer,
            judge=judge,
            memory=memory,
            validator=validator
        )
        return agent
    except Exception as e:
        logger.error(f"Failed to create Transient Agent: {e}")
        raise HTTPException(status_code=500, detail="Agent instantiation failed")

# --- Startup ---
# Startup warm-up sequence
async def initialize_global_agent():
    """
    Initializes and validates global service providers.
    """
    try:
        config = get_config()
        get_db(config)
        get_llm(config)
        get_knowledge_base(config)
        get_context_builder()
        get_analyzer(config)
        get_judge(config)
        get_memory(config)
        get_validator()
        logger.info("Global Services Warmed Up Successfully.")
    except Exception as e:
        logger.critical(f"Startup Warmup Failed: {e}")
        # Critical failure if DB/LLM cannot initialize
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

