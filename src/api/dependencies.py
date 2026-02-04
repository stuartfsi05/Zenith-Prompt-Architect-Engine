from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
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

def get_llm(
    config: Config = Depends(get_config),
    api_key: Optional[str] = Security(APIKeyHeader(name="x-google-api-key", auto_error=False))
) -> GoogleGenAIProvider:
    """
    Transient LLM Provider.
    Creates a new instance for every request to support dynamic API Keys.
    Priority: Header 'x-google-api-key' > Config.GOOGLE_API_KEY > Error
    """
    try:
        final_api_key = None
        
        # Check if api_key is a valid string (not the default Security object)
        if isinstance(api_key, str) and api_key.strip():
            final_api_key = api_key
        
        # Fallback to config
        if not final_api_key:
             if config.GOOGLE_API_KEY:
                final_api_key = config.GOOGLE_API_KEY.get_secret_value()
        
        if not final_api_key:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Google API Key. Provide 'x-google-api-key' header or configure server default."
            )

        logger.debug(f"Initializing Transient GoogleGenAIProvider ({config.MODEL_NAME}). Key provided: {'Yes (Header)' if api_key else 'Yes (Default)'}")
        
        # Load default system prompt
        default_sys_prompt = load_system_prompt(config.SYSTEM_PROMPT_PATH)
        
        provider = GoogleGenAIProvider(
            model_name=config.MODEL_NAME,
            temperature=config.TEMPERATURE,
            system_instruction=default_sys_prompt
        )
        provider.configure(final_api_key)
        return provider
    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"Failed to initialize LLM: {e}")
        raise HTTPException(status_code=500, detail="LLM initialization failed")

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
        # Pass explicit None to trigger fallback logic and avoid Security object issue
        get_llm(config, api_key=None)
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

