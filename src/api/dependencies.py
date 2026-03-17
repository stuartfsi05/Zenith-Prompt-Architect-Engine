import logging
from typing import Dict, Optional, Any

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from src.core.agent import ZenithAgent
from src.core.analyzer import StrategicAnalyzer
from src.core.config import Config
from src.core.context_builder import ContextBuilder
from src.core.database import SupabaseRepository
from src.core.judge import TheJudge
from src.core.knowledge.manager import StrategicKnowledgeBase
from src.core.llm.google_genai import GoogleGenAIProvider
from src.core.memory import StrategicMemory
from src.core.services.auth import AuthService
from src.core.validator import SemanticValidator
from src.utils.loader import load_system_prompt

# Logger for API logic
logger = logging.getLogger("ZenithAPI")

# Internal registry for singleton service instances
_singletons: Dict[str, Any] = {}


def get_config() -> Config:
    """
    Returns the global application configuration.

    The configuration is loaded once and cached in the singleton registry.

    Returns:
        Config: The application configuration instance.
    """
    if "config" not in _singletons:
        _singletons["config"] = Config()
    return _singletons["config"]


def get_db(config: Config = Depends(get_config)) -> SupabaseRepository:
    """
    Provides a singleton Database Repository instance.

    Args:
        config (Config): The application configuration.

    Returns:
        SupabaseRepository: The initialized database interface.

    Raises:
        RuntimeError: If the database repository fails to initialize.
    """
    if "db" not in _singletons:
        try:
            logger.info("Initializing persistent registry: SupabaseRepository.")
            _singletons["db"] = SupabaseRepository(config)
        except Exception as e:
            logger.critical(f"Critical Error: Persistence Layer failed to boot: {e}")
            raise RuntimeError("Database initialization failed") from e
    return _singletons["db"]


def get_llm(
    config: Config = Depends(get_config),
    api_key: Optional[str] = Security(APIKeyHeader(name="x-google-api-key", auto_error=False)),
) -> GoogleGenAIProvider:
    """
    Provides a transient LLM Provider instance for the current request.

    Features dynamic API key extraction from the 'x-google-api-key' header,
    falling back to server-side environment variables if the header is absent.

    Args:
        config (Config): Application configuration.
        api_key (Optional[str]): Custom API key provided in the request headers.

    Returns:
        GoogleGenAIProvider: Specialized GenAI interface.

    Raises:
        HTTPException: If no API key is found or initialization fails.
    """
    try:
        # Determine effective API Key
        final_api_key = None
        if isinstance(api_key, str) and api_key.strip():
            final_api_key = api_key
        elif config.GOOGLE_API_KEY:
            final_api_key = config.GOOGLE_API_KEY.get_secret_value()

        if not final_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Google API Key. Provide 'x-google-api-key' header or contact the admin.",
            )

        logger.debug(
            f"Instantiating GenAI Provider ({config.MODEL_NAME}). "
            f"Key source: {'Request Header' if api_key else 'Global Config'}."
        )

        # Pre-load core instruction set
        default_sys_prompt = load_system_prompt(config.SYSTEM_PROMPT_PATH)

        provider = GoogleGenAIProvider(
            model_name=config.MODEL_NAME,
            temperature=config.TEMPERATURE,
            system_instruction=default_sys_prompt,
        )
        provider.configure(final_api_key)
        return provider

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"GenAI Initialization Crash: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER__ERROR,
            detail="Neural Engine initialization failed.",
        )


def get_auth_service(config: Config = Depends(get_config)) -> AuthService:
    """Provides a singleton Authentication Service."""
    if "auth_service" not in _singletons:
        _singletons["auth_service"] = AuthService(config)
    return _singletons["auth_service"]


def get_knowledge_base(config: Config = Depends(get_config)) -> StrategicKnowledgeBase:
    """Provides a singleton RAG Retrieval Engine."""
    if "knowledge_base" not in _singletons:
        _singletons["knowledge_base"] = StrategicKnowledgeBase(config)
    return _singletons["knowledge_base"]


def get_context_builder() -> ContextBuilder:
    """Provides a singleton Prompt Architect/Context Builder."""
    if "context_builder" not in _singletons:
        _singletons["context_builder"] = ContextBuilder()
    return _singletons["context_builder"]


def get_analyzer(config: Config = Depends(get_config)) -> StrategicAnalyzer:
    """Provides a singleton Strategic Intent Analyzer."""
    if "analyzer" not in _singletons:
        _singletons["analyzer"] = StrategicAnalyzer(config)
    return _singletons["analyzer"]


def get_judge(config: Config = Depends(get_config)) -> TheJudge:
    """Provides a singleton Quality Evaluation Engine."""
    if "judge" not in _singletons:
        _singletons["judge"] = TheJudge(config)
    return _singletons["judge"]


def get_memory(config: Config = Depends(get_config)) -> StrategicMemory:
    """Provides a singleton Episodic/Semantic Memory Service."""
    if "memory" not in _singletons:
        _singletons["memory"] = StrategicMemory(config)
    return _singletons["memory"]


def get_validator() -> SemanticValidator:
    """Provides a singleton Input/Output Consistency Validator."""
    if "validator" not in _singletons:
        _singletons["validator"] = SemanticValidator()
    return _singletons["validator"]


# --- Request-Scoped (Transient) dependencies ---


def get_agent(
    config: Config = Depends(get_config),
    db: SupabaseRepository = Depends(get_db),
    llm: GoogleGenAIProvider = Depends(get_llm),
    knowledge_base: StrategicKnowledgeBase = Depends(get_knowledge_base),
    context_builder: ContextBuilder = Depends(get_context_builder),
    analyzer: StrategicAnalyzer = Depends(get_analyzer),
    judge: TheJudge = Depends(get_judge),
    memory: StrategicMemory = Depends(get_memory),
    validator: SemanticValidator = Depends(get_validator),
) -> ZenithAgent:
    """
    Factory dependency that builds a new ZenithAgent per request.

    This ensures complete request isolation while sharing heavy singleton services
    (Database, Analyzers, Memory controllers) across the application.

    Returns:
        ZenithAgent: An orchestrator instance ready for processing.
    """
    try:
        system_instruction = load_system_prompt(config.SYSTEM_PROMPT_PATH)

        return ZenithAgent(
            config=config,
            system_instruction=system_instruction,
            db=db,
            llm=llm,
            knowledge_base=knowledge_base,
            context_builder=context_builder,
            analyzer=analyzer,
            judge=judge,
            memory=memory,
            validator=validator,
        )
    except Exception as e:
        logger.error(f"Agent Orchestrator Assembly Failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize the Zenith Processing Unit.",
        )


async def initialize_global_agent() -> None:
    """
    Performs a warm-up sequence for all global singleton services.

    Expected to be called during application startup (lifespan) to verify
    connectivity to external providers (Database, LLM) immediately.
    """
    try:
        config = get_config()
        get_db(config)
        # Verify LLM availability (checks if API key exists in environment)
        get_llm(config, api_key=None)
        get_knowledge_base(config)
        get_context_builder()
        get_analyzer(config)
        get_judge(config)
        get_memory(config)
        get_validator()
        logger.info("Universal Service Discovery: All core modules are ONLINE.")
    except Exception as e:
        logger.critical(f"Lifespan Initialization Failure: {e}")
        raise e


# --- Authentication Context ---

security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> Any:
    """
    Authentication Guard: Verifies the Bearer token against the Auth Provider.

    Returns:
        Any: User metadata if authorized.

    Raises:
        HTTPException: For invalid or expired tokens.
    """
    return auth_service.verify_token(credentials.credentials)


