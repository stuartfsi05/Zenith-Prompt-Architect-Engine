import asyncio
import logging
from typing import AsyncGenerator, Optional, Dict, Any

from src.core.analyzer import StrategicAnalyzer
from src.core.config import Config
from src.core.context_builder import ContextBuilder
from src.core.database import PersistenceLayer
from src.core.judge import TheJudge
from src.core.knowledge.manager import StrategicKnowledgeBase
from src.core.llm.provider import LLMProvider
from src.core.memory import StrategicMemory
from src.core.personas import Personas
from src.core.services.history import HistoryService
from src.core.services.usage import UsageService
from src.core.validator import SemanticValidator
from src.utils.logger import setup_logger

# Initialize logger for the agent core
logger = setup_logger("ZenithAgent")


class ZenithAgent:
    """
    The orchestrator for the Zenith autonomous system.

    Coordinates intent analysis, history management, situational memory,
    knowledge retrieval (RAG), and response self-correction. Designed as a
    transient service that maintains session state during a single interaction lifecycle.
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
        validator: SemanticValidator,
    ):
        """
        Initializes the agent with its core dependencies via injection.
        """
        if not db:
            raise ValueError("Dependency 'db' (PersistenceLayer) cannot be None.")
        if not llm:
            raise ValueError("Dependency 'llm' (LLMProvider) cannot be None.")

        self.config = config
        self.default_system_instruction = system_instruction
        self.db = db
        self.llm = llm

        # Logic Components
        self.knowledge_base = knowledge_base
        self.context_builder = context_builder
        self.analyzer = analyzer
        self.validator = validator
        self.judge = judge
        self.memory = memory

        # Domain Services
        self.usage_service = UsageService(self.db)
        self.history_service = HistoryService(self.db)

        # Session State
        self.current_session_id: Optional[str] = None
        self.main_session: Any = None

        logger.debug("ZenithAgent instance initialized via dependency injection.")

    def start_chat(self, session_id: str, user_id: str) -> None:
        """
        Prepares the agent for a new or existing chat session.
        """
        self.current_session_id = session_id
        formatted_history = self.history_service.get_formatted_history(session_id, user_id)

        # Initialize isolated chat session
        self.main_session = self.llm.start_chat(history=formatted_history)
        logger.info(f"Chat session '{session_id}' started. History restored: {len(formatted_history)} items.")

    async def run_analysis_async(
        self, user_input: str, user_id: str, session_id: str
    ) -> AsyncGenerator[str, None]:
        """
        The main pipeline for processing user input and streaming a response.
        """
        # 1. State Sync
        if self.current_session_id != session_id or not self.main_session:
            self.start_chat(session_id, user_id)

        await self.memory.manage_history(self.main_session)
        logger.info(f"Analyzing Input (Session: {session_id}): {user_input[:50]}...")

        # 2. Input Shielding
        if not self.validator.validate_user_input(user_input):
            yield "⚠️ **Input Blocked:** Your message triggered our safety protocols."
            return

        # 3. Concurrent Retrieval & Analysis
        analyzer_task = asyncio.create_task(self.analyzer.analyze_intent_async(user_input))
        knowledge_task = asyncio.create_task(self.knowledge_base.retrieve_async(user_input))

        try:
            analysis_result = await analyzer_task
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            analysis_result = self.analyzer._get_fallback_response(user_input)

        nature = analysis_result.get("natureza", "Raciocínio")
        complexity = analysis_result.get("complexidade", "Composta")

        # 4. Neural Context Assembly
        selected_persona = Personas.get_persona(nature)
        system_injection = self.context_builder.build_system_injection(selected_persona)

        rag_context = await self.context_builder.resolve_rag_context(knowledge_task, complexity)
        memory_context = self.memory.get_context_injection()

        final_prompt = self.context_builder.assemble_prompt(
            system_injection, memory_context, rag_context, user_input
        )

        # 5. Log Interaction (User)
        self.db.log_interaction(self.current_session_id, user_id, "user", user_input)

        # 6. Streamed Generation and Quality Guardrails
        full_response_text = ""
        metadata: Dict[str, Any] = {}

        try:
            async for chunk in self._generate_with_retry(
                final_prompt, user_input, user_id, session_id, metadata
            ):
                yield chunk
                if isinstance(chunk, str):
                    full_response_text += chunk

            # Background task for memory consolidation
            asyncio.create_task(self.memory.extract_entities_async(user_input, full_response_text))

        except Exception as e:
            logger.critical(f"Agent Pipeline Failure: {e}")
            yield f"\n⚠️ **Critical System Failure**: {str(e)}"
            metadata["status"] = "failed"
            metadata["error_msg"] = str(e)
        finally:
            if full_response_text:
                self.db.log_interaction(
                    self.current_session_id,
                    user_id,
                    "model",
                    full_response_text,
                    metadata=metadata,
                )

    async def _generate_with_retry(
        self, prompt: str, original_input: str, user_id: str, session_id: str, metadata: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """
        Executes generation with feedback-driven refinement (Self-Correction loop).
        """
        stream = self.llm.send_message_async(self.main_session, prompt, stream=True)
        full_response = ""

        # Phase 1: Initial Stream
        async for chunk in stream:
            if isinstance(chunk, dict) and "usage_metadata" in chunk:
                self.usage_service.log_tokens(
                    user_id, session_id, self.config.MODEL_NAME, chunk["usage_metadata"]
                )
                continue
            if isinstance(chunk, str):
                yield chunk
                full_response += chunk

        # Phase 2: Quality Evaluation
        evaluation = await self.judge.evaluate_async(original_input, full_response)
        score = evaluation.get("score", 0)
        feedback = evaluation.get("feedback", "")
        needs_refinement = evaluation.get("needs_refinement", False)

        metadata["score"] = score
        metadata["judge_feedback"] = feedback

        # Phase 3: Self-Correction Loop (Refinement)
        quality_bar = 80
        if score < quality_bar or needs_refinement:
            yield f"\n\n*⚠️ Quality Assurance detected issues (Score: {score}). Refining...*\n\n"

            refinement_prompt = (
                "--- [SELF-CORRECTION PROTOCOL] ---\n"
                f"Analyze your previous response. The Quality Judge rejected it (Score: {score}).\n"
                f"CRITICAL FEEDBACK: {feedback}\n"
                "TASK: Rewrite the response leveraging your internal reasoning to fix these errors."
            )

            # Circuit Breaker: We buffer the retry to ensure high quality before showing user
            retry_buffer = ""
            try:
                retry_stream = self.llm.send_message_async(self.main_session, refinement_prompt, stream=True)
                async for chunk in retry_stream:
                    if isinstance(chunk, dict) and "usage_metadata" in chunk:
                        self.usage_service.log_tokens(
                            user_id, session_id, self.config.MODEL_NAME, chunk["usage_metadata"]
                        )
                        continue
                    if isinstance(chunk, str):
                        retry_buffer += chunk

                # Validate the refinement
                retry_eval = await self.judge.evaluate_async(original_input, retry_buffer)
                final_score = retry_eval.get("score", 0)

                if final_score >= quality_bar:
                    yield retry_buffer
                    yield (
                        f"\n\n### Painel de Qualidade (Pós-Refinamento)\n"
                        f"- **Pontuação Final**: {final_score}/100\n"
                        f"- **Status**: Aprovado\n"
                    )
                else:
                    logger.warning(f"Circuit Breaker: Refinement failed (Score: {final_score})")
                    yield (
                        "\n\n**⛔ Circuit Breaker Activated**\n"
                        "We were unable to generate a response that meets our quality standards. "
                        "Please try rephrasing your request."
                    )
                    metadata["failure_reason"] = "refinement_insufficient"

            except Exception as e:
                logger.error(f"Response refinement crashed: {e}")
                yield f"\n\n**Error:** The refinement process encountered a problem: {str(e)}"
                metadata["refinement_error"] = str(e)
        else:
            # Display Quality Panel for approved initial response
            yield (
                f"\n\n### Painel de Qualidade\n"
                f"- **Pontuação**: {score}/100\n"
                f"- **Análise**: {feedback}\n"
            )
