import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from src.core.agent import ZenithAgent
from src.core.analyzer import StrategicAnalyzer
from src.core.config import Config
from src.core.context_builder import ContextBuilder
from src.core.database import PersistenceLayer, SupabaseRepository
from src.core.judge import TheJudge
from src.core.knowledge.manager import StrategicKnowledgeBase
from src.core.knowledge.reranker import RerankerService
from src.core.llm.google_genai import GoogleGenAIProvider
from src.core.memory import StrategicMemory
from src.core.services.auth import AuthService
from src.core.services.quota import DemoQuotaService
from src.core.validator import SemanticValidator
from src.utils.loader import load_system_prompt

logger = logging.getLogger("ZenithAPI")

_singletons: Dict[str, Any] = {}


@dataclass(frozen=True)
class RequestLLMContext:
    """Resolved execution mode, API key, and primary model for the current request."""

    mode: str
    api_key: str
    primary_model: str
    primary_thinking_level: str


def get_config() -> Config:
    """Returns the cached global application configuration."""
    if "config" not in _singletons:
        _singletons["config"] = Config()
    return _singletons["config"]


def get_db(config: Config = Depends(get_config)) -> SupabaseRepository:
    """Provides a singleton Database Repository instance."""
    if "db" not in _singletons:
        try:
            logger.info("Initializing persistent registry: SupabaseRepository.")
            _singletons["db"] = SupabaseRepository(config)
        except Exception as e:
            logger.critical(f"Critical Error: Persistence Layer failed to boot: {e}")
            raise RuntimeError("Database initialization failed") from e
    return _singletons["db"]


def get_quota_service(
    config: Config = Depends(get_config),
    db: PersistenceLayer = Depends(get_db),
) -> DemoQuotaService:
    """Provides the singleton Demo Mode daily quota service."""
    if "quota_service" not in _singletons:
        _singletons["quota_service"] = DemoQuotaService(
            db=db, daily_limit=config.DEMO_DAILY_LIMIT
        )
    return _singletons["quota_service"]


def get_llm_context(
    config: Config = Depends(get_config),
    api_key: Optional[str] = Security(
        APIKeyHeader(name="x-google-api-key", auto_error=False)
    ),
) -> RequestLLMContext:
    """
    Resolves whether the request uses BYOK (user key -> Gemini 3.8 Flash)
    or zero-friction Demo Mode (server key -> Gemini 3.5 Flash-Lite).
    """
    if isinstance(api_key, str) and api_key.strip():
        return RequestLLMContext(
            mode="byok",
            api_key=api_key.strip(),
            primary_model=config.MODEL_NAME,
            primary_thinking_level=config.THINKING_LEVEL,
        )

    return RequestLLMContext(
        mode="demo",
        api_key=config.GOOGLE_API_KEY.get_secret_value(),
        primary_model=config.AUX_MODEL_NAME,
        primary_thinking_level="low",
    )


def get_llm(
    config: Config = Depends(get_config),
    llm_ctx: RequestLLMContext = Depends(get_llm_context),
) -> GoogleGenAIProvider:
    """Provides a transient LLM Provider instance configured for the request mode."""
    try:
        logger.debug(
            f"Instantiating GenAI Provider ({llm_ctx.primary_model}) "
            f"in mode={llm_ctx.mode}."
        )
        default_sys_prompt = load_system_prompt(str(config.SYSTEM_PROMPT_PATH))

        provider = GoogleGenAIProvider(
            model_name=llm_ctx.primary_model,
            temperature=config.TEMPERATURE,
            system_instruction=default_sys_prompt,
            thinking_level=llm_ctx.primary_thinking_level,
        )
        provider.configure(llm_ctx.api_key)
        return provider

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"GenAI Initialization Crash: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Neural Engine initialization failed.",
        )


def create_cli_llm(config: Config) -> GoogleGenAIProvider:
    """Builds the primary LLM Provider for local CLI execution."""
    default_sys_prompt = load_system_prompt(str(config.SYSTEM_PROMPT_PATH))
    provider = GoogleGenAIProvider(
        model_name=config.MODEL_NAME,
        temperature=config.TEMPERATURE,
        system_instruction=default_sys_prompt,
        thinking_level=config.THINKING_LEVEL,
    )
    provider.configure(config.GOOGLE_API_KEY.get_secret_value())
    return provider


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
    """Provides a singleton Strategic Intent Analyzer for server-key Demo mode."""
    if "analyzer" not in _singletons:
        _singletons["analyzer"] = StrategicAnalyzer(config)
    return _singletons["analyzer"]


def get_judge(config: Config = Depends(get_config)) -> TheJudge:
    """Provides a singleton Quality Evaluation Engine for server-key Demo mode."""
    if "judge" not in _singletons:
        _singletons["judge"] = TheJudge(config)
    return _singletons["judge"]


def get_memory(
    config: Config = Depends(get_config),
    db: PersistenceLayer = Depends(get_db),
) -> StrategicMemory:
    """Provides a singleton multi-tenant Semantic Memory Service."""
    if "memory" not in _singletons:
        _singletons["memory"] = StrategicMemory(config, db=db)
    return _singletons["memory"]


def get_validator() -> SemanticValidator:
    """Provides a singleton Input/Output Consistency Validator."""
    if "validator" not in _singletons:
        _singletons["validator"] = SemanticValidator()
    return _singletons["validator"]


security_scheme = HTTPBearer()


def get_user_db(
    config: Config = Depends(get_config),
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> SupabaseRepository:
    """Provides a request-scoped SupabaseRepository authenticated with the user JWT."""
    return SupabaseRepository(config, access_token=credentials.credentials)


def get_agent(
    config: Config = Depends(get_config),
    db: SupabaseRepository = Depends(get_user_db),
    llm_ctx: RequestLLMContext = Depends(get_llm_context),
    llm: GoogleGenAIProvider = Depends(get_llm),
    knowledge_base: StrategicKnowledgeBase = Depends(get_knowledge_base),
    context_builder: ContextBuilder = Depends(get_context_builder),
    analyzer: StrategicAnalyzer = Depends(get_analyzer),
    judge: TheJudge = Depends(get_judge),
    validator: SemanticValidator = Depends(get_validator),
) -> ZenithAgent:
    """
    Factory dependency that builds a request-isolated ZenithAgent.

    In BYOK mode, Analyzer, Judge, Reranker, and Memory use the user's API key
    so zero server quota is consumed. In Demo mode, server singletons are shared
    for Analyzer/Judge while StrategicMemory remains bound to the user-JWT DB.
    """
    try:
        system_instruction = load_system_prompt(str(config.SYSTEM_PROMPT_PATH))

        if llm_ctx.mode == "byok":
            active_analyzer = StrategicAnalyzer(config, api_key=llm_ctx.api_key)
            active_judge = TheJudge(config, api_key=llm_ctx.api_key)
            active_memory = StrategicMemory(config, db=db, api_key=llm_ctx.api_key)
            reranker_override: Optional[RerankerService] = RerankerService(
                config, api_key=llm_ctx.api_key
            )
        else:
            active_analyzer = analyzer
            active_judge = judge
            active_memory = StrategicMemory(config, db=db)
            reranker_override = None

        return ZenithAgent(
            config=config,
            system_instruction=system_instruction,
            db=db,
            llm=llm,
            knowledge_base=knowledge_base,
            context_builder=context_builder,
            analyzer=active_analyzer,
            judge=active_judge,
            memory=active_memory,
            validator=validator,
            active_model_name=llm_ctx.primary_model,
            mode=llm_ctx.mode,
            reranker_override=reranker_override,
        )
    except Exception as e:
        logger.error(f"Agent Orchestrator Assembly Failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize the Zenith Processing Unit.",
        )


async def initialize_global_agent() -> None:
    """
    Performs a warm-up sequence for all global singleton services during startup.
    """
    try:
        config = get_config()
        db = get_db(config)
        get_quota_service(config, db)
        get_knowledge_base(config)
        get_context_builder()
        get_analyzer(config)
        get_judge(config)
        get_memory(config, db)
        get_validator()
        logger.info("Universal Service Discovery: All core modules are ONLINE.")
    except Exception as e:
        logger.critical(f"Lifespan Initialization Failure: {e}")
        raise e


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> Any:
    """
    Authentication Guard: Verifies the Bearer token against Supabase Auth.
    """
    return await asyncio.to_thread(auth_service.verify_token, credentials.credentials)
