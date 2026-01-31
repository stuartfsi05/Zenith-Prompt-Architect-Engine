from typing import Optional, AsyncGenerator

from src.core.analyzer import StrategicAnalyzer
from src.core.config import Config
from src.core.judge import TheJudge
from src.core.knowledge.manager import StrategicKnowledgeBase
from src.core.llm.google_genai import GoogleGenAIProvider
from src.core.memory import StrategicMemory
from src.core.personas import Personas
from src.core.validator import SemanticValidator
from src.core.database import SupabaseRepository
from src.core.services.usage import UsageService
from src.core.services.history import HistoryService

from src.utils.logger import setup_logger

logger = setup_logger("ZenithAgent")


class ZenithAgent:
    """
    Main agent class that coordinates analysis, memory, knowledge retrieval,
    and response generation.
    Designed as a Transient Service: Created per request, disposed after.
    """

    def __init__(
        self, 
        config: Config, 
        system_instruction: str,
        db: SupabaseRepository,
        llm: GoogleGenAIProvider
    ):
        """
        Initialize the Agent with INJECTED dependencies.
        NO internal instantiation of IO heavy services allowed.
        """
        if not db:
            raise ValueError("Dependency 'db' (SupabaseRepository) cannot be None.")
        if not llm:
            raise ValueError("Dependency 'llm' (GoogleGenAIProvider) cannot be None.")

        self.config = config
        self.default_system_instruction = system_instruction
        self.db = db
        self.llm = llm

        # Logic Components (Can be instantiated internally as they are mostly logic/config,
        # but ideally should also be injected if they become heavy).
        # For now, per instructions, we keep logic components here.
        self.analyzer = StrategicAnalyzer(self.config)
        self.validator = SemanticValidator()
        self.judge = TheJudge(self.config)
        self.knowledge_base = StrategicKnowledgeBase(self.config)
        self.memory = StrategicMemory(self.config)
        
        # Services - We re-instantiate them with the injected DB. 
        # Since they are lightweight wrappers around the DB, this is acceptable for now.
        # Alternatively, inject them too? The prompt focused on DB/LLM. 
        # Re-creating them is cheap and safe as long as DB is shared.
        self.usage_service = UsageService(self.db)
        self.history_service = HistoryService(self.db)

        # Session State - Transient per agent instance
        self.current_session_id: Optional[str] = None
        self.main_session = None

        logger.debug(f"ZenithAgent initialized for session context.")

    def start_chat(self, session_id: str, user_id: str):
        """
        Starts the chat session and loads history from the database.
        """
        self.current_session_id = session_id
        # logger.info(f"Loading Session: {session_id} for User: {user_id}") 
        # Reduced logging for transient creations

        # Use HistoryService
        formatted_history = self.history_service.get_formatted_history(session_id, user_id)

        # Use LLM Provider
        # IMPORTANT: start_chat returns a NEW AsyncChat session.
        # This is local to this Agent instance.
        self.main_session = self.llm.start_chat(history=formatted_history)
        logger.info(f"Context Restored ({len(formatted_history)} items).")

    def _prune_history(self):
        """
        Prunes history if it exceeds limits. 
        Delegates memory consolidation.
        """
        # Kept internal for now as it touches main_session state directly
        max_history = 20
        history_len = len(self.main_session._curated_history)

        if history_len > max_history:
            prune_count = history_len - max_history
            items_to_prune = self.main_session._curated_history[:prune_count]

            logger.info(
                f"Pruning History (Current: {history_len}). "
                f"Archiving {len(items_to_prune)} items."
            )
            asyncio.create_task(self.memory.consolidate_memory_async(items_to_prune))
            self.main_session._curated_history = self.main_session._curated_history[prune_count:]

    async def run_analysis_async(self, user_input: str, user_id: str, session_id: str) -> AsyncGenerator[str, None]:
        """
        Process user input through analysis, retrieval, and generation steps.
        """
        # 1. Session Management
        if self.current_session_id != session_id or not self.main_session:
             self.start_chat(session_id, user_id)
             
        self._prune_history()
        logger.info(f"Processing Input: {user_input[:50]}...")

        # 2. Validation
        if not self.validator.validate_user_input(user_input):
            yield "⚠️ Input blocked by Safety Protocols."
            return

        # 3. Analysis & Retrieval (Concurrent)
        analyzer_task = asyncio.create_task(self.analyzer.analyze_intent_async(user_input))
        knowledge_task = asyncio.create_task(self.knowledge_base.retrieve_async(user_input))

        try:
            analysis_result = await analyzer_task
        except Exception as e:
            logger.error(f"Analyzer failed: {e}")
            analysis_result = self.analyzer._get_fallback_response(user_input)

        nature = analysis_result.get("natureza", "Raciocínio")
        complexity = analysis_result.get("complexidade", "Composta")

        # 4. Context Construction
        selected_persona = Personas.get_persona(nature)
        system_injection = self._build_system_injection(selected_persona)

        rag_context = await self._resolve_rag_context(knowledge_task, complexity)
        memory_context = self.memory.get_context_injection()
        
        final_prompt = f"{system_injection}\n\n{memory_context}\n{rag_context}\n--- [USER REQUEST] ---\n{user_input}"
        
        # 5. Interaction Logging
        self.db.log_interaction(self.current_session_id, user_id, "user", user_input)

        # 6. LLM Generation & Self-Correction
        full_response_text = ""
        metadata = {}
        
        try:
            async for chunk in self._generate_with_retry(final_prompt, user_input, user_id, session_id, metadata):
                yield chunk
                if isinstance(chunk, str):
                    full_response_text += chunk

            asyncio.create_task(
                self.memory.extract_entities_async(user_input, full_response_text)
            )

        except Exception as e:
            logger.critical(f"Critical Unexpected Error: {e}")
            yield f"\n⚠️ **Critical Failure**: Please contact support. ({str(e)})"
            metadata["error"] = str(e)

        finally:
            if full_response_text:
                self.db.log_interaction(
                    self.current_session_id,
                    user_id,
                    "model",
                    full_response_text,
                    metadata=metadata,
                )

    def _build_system_injection(self, persona: str) -> str:
        return (
            f"--- [SYSTEM OVERRIDE: ACTIVE PERSONA] ---\n{persona}\n\n"
            f"--- [MANDATORY INSTRUCTION: DEEP THINKING] ---\n"
            f"Antes de responder, você DEVE analisar o pedido passo a passo "
            f"dentro de tags <thinking>...</thinking>.\n"
            f"Planeje sua resposta, verifique fatos e critique sua própria lógica.\n"
            f"Apenas após o fechamento da tag </thinking>, forneça a resposta final ao usuário.\n"
        )

    async def _resolve_rag_context(self, knowledge_task: asyncio.Task, complexity: str) -> str:
        rag_context = ""
        if complexity != "Simples":
            try:
                content = await knowledge_task
                if content:
                    rag_context = f"--- [RELEVANT CONTEXT (Hybrid Search)] ---\n{content}\n\n"
            except Exception as e:
                logger.error(f"Knowledge Retrieval failed: {e}")
        else:
            # We still await to ensure task cleanup, but ignore result
            try:
                await knowledge_task
            except Exception:
                pass
        return rag_context

    async def _generate_with_retry(self, prompt: str, original_input: str, user_id: str, session_id: str, metadata: dict):
        """
        Handles generation loop, streaming, token usage logging, and self-correction.
        """
        stream = self.llm.send_message_async(self.main_session, prompt, stream=True)
        
        full_response = ""
        
        # Primary Generation
        async for chunk in stream:
            if isinstance(chunk, dict) and "usage_metadata" in chunk:
                self.usage_service.log_tokens(user_id, session_id, self.config.MODEL_NAME, chunk["usage_metadata"])
                continue
            if isinstance(chunk, str):
                yield chunk
                full_response += chunk

        # Evaluation
        evaluation = await self.judge.evaluate_async(original_input, full_response)
        score = evaluation.get("score", 0)
        feedback = evaluation.get("feedback", "")
        needs_refinement = evaluation.get("needs_refinement", False)

        metadata["score"] = score
        metadata["feedback"] = feedback
        
        # Self-Correction Loop
        min_score = 80
        if score < min_score or needs_refinement:
             yield f"\n\n[dim]⚠️ Quality Assurance detected issues (Score: {score}). Refining...[/dim]\n\n"
             
             # Simple retry logic (could be expanded)
             refinement_prompt = (
                f"--- [SELF-CORRECTION PROTOCOL] ---\n"
                f"Analyze your previous response. The Quality Judge rejected it (Score: {score}).\n"
                f"CRITICAL FEEDBACK: {feedback}\n"
                f"TASK: Rewrite the response leveraging your <thinking> process to fix these errors."
             )
             
             retry_stream = self.llm.send_message_async(self.main_session, refinement_prompt, stream=True)
             async for chunk in retry_stream:
                if isinstance(chunk, dict) and "usage_metadata" in chunk:
                    self.usage_service.log_tokens(user_id, session_id, self.config.MODEL_NAME, chunk["usage_metadata"])
                    continue
                if isinstance(chunk, str):
                    yield chunk
