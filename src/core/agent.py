import asyncio

from typing import Optional, AsyncGenerator

from src.core.context_builder import ContextBuilder
from src.core.analyzer import StrategicAnalyzer
from src.core.config import Config
from src.core.judge import TheJudge
from src.core.knowledge.manager import StrategicKnowledgeBase
from src.core.llm.provider import LLMProvider
from src.core.memory import StrategicMemory
from src.core.personas import Personas
from src.core.validator import SemanticValidator
from src.core.database import PersistenceLayer
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
        db: PersistenceLayer,
        llm: LLMProvider,
        knowledge_base: StrategicKnowledgeBase,
        context_builder: ContextBuilder,
        analyzer: StrategicAnalyzer,
        judge: TheJudge,
        memory: StrategicMemory,
        validator: SemanticValidator
    ):
        """
        Initialize the Agent with injected dependencies.
        Enforce dependency injection for IO-bound services.
        """
        if not db:
            raise ValueError("Dependency 'db' (PersistenceLayer) cannot be None.")
        if not llm:
            raise ValueError("Dependency 'llm' (LLMProvider) cannot be None.")

        self.config = config
        self.default_system_instruction = system_instruction
        self.db = db
        self.llm = llm

        # Initialize logical components (Injected)
        self.knowledge_base = knowledge_base
        self.context_builder = context_builder
        self.analyzer = analyzer
        self.validator = validator
        self.judge = judge
        self.memory = memory
        
        # Initialize domain services using the injected DB repository
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

        # Use HistoryService
        formatted_history = self.history_service.get_formatted_history(session_id, user_id)

        # Use LLM Provider
        # Initializes a new isolated AsyncChat session for this agent instance.
        self.main_session = self.llm.start_chat(history=formatted_history)
        logger.info(f"Context Restored ({len(formatted_history)} items).")



    async def run_analysis_async(self, user_input: str, user_id: str, session_id: str) -> AsyncGenerator[str, None]:
        """
        Process user input through analysis, retrieval, and generation steps.
        """
        # 1. Session Management
        if self.current_session_id != session_id or not self.main_session:
             self.start_chat(session_id, user_id)
             
        await self.memory.manage_history(self.main_session)
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
        system_injection = self.context_builder.build_system_injection(selected_persona)

        rag_context = await self.context_builder.resolve_rag_context(knowledge_task, complexity)
        memory_context = self.memory.get_context_injection()
        
        final_prompt = self.context_builder.assemble_prompt(
            system_injection, memory_context, rag_context, user_input
        )
        
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
             
             refinement_prompt = (
                f"--- [SELF-CORRECTION PROTOCOL] ---\n"
                f"Analyze your previous response. The Quality Judge rejected it (Score: {score}).\n"
                f"CRITICAL FEEDBACK: {feedback}\n"
                f"TASK: Rewrite the response leveraging your <thinking> process to fix these errors."
             )
             
             # --- Circuit Breaker Pattern ---
             # Buffer the response to validate BEFORE streaming to user.
             # This prevents "Fail-Open" where we stream garbage.
             retry_response_buffer = ""
             try:
                 retry_stream = self.llm.send_message_async(self.main_session, refinement_prompt, stream=True)
                 async for chunk in retry_stream:
                    if isinstance(chunk, dict) and "usage_metadata" in chunk:
                        self.usage_service.log_tokens(user_id, session_id, self.config.MODEL_NAME, chunk["usage_metadata"])
                        continue
                    if isinstance(chunk, str):
                        retry_response_buffer += chunk
                 
                 # Secondary Evaluation (Circuit Breaker)
                 retry_eval = await self.judge.evaluate_async(original_input, retry_response_buffer)
                 retry_score = retry_eval.get("score", 0)
                 
                 if retry_score >= min_score:
                     yield retry_response_buffer
                     # Append Quality Panel for Retried Response
                     yield f"\n\n### Painel de Qualidade (Avaliação do Juiz)\n- **Pontuação Final**: {retry_score}/100\n- **Feedback**: {retry_eval.get('feedback', 'Aprovado após refinamento.')}\n"
                 else:
                     logger.warning(f"Circuit Breaker Triggered: Retry Score {retry_score} < {min_score}")
                     yield (
                         "\n\n[bold red]⛔ Circuit Breaker Activated[/bold red]\n"
                         "Unable to formulate a response that meets safety/quality standards after refinement.\n"
                         "Please rephrase your request."
                     )
                     metadata["circuit_breaker_triggered"] = True

             except Exception as e:
                 logger.error(f"Refinement failed: {e}")
                 yield f"\n\n[error]Refinement process failed: {str(e)}[/error]"
                 metadata["error_refinement"] = str(e)
        else:
            # Append Quality Panel for Original Response
            yield f"\n\n### Painel de Qualidade (Avaliação do Juiz)\n- **Pontuação Final**: {score}/100\n- **Feedback**: {feedback}\n"
