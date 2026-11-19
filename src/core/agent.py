import asyncio
from typing import Any, AsyncGenerator, Dict, Optional

from src.core.analyzer import StrategicAnalyzer
from src.core.config import Config
from src.core.context_builder import ContextBuilder
from src.core.database import PersistenceLayer
from src.core.judge import TheJudge
from src.core.knowledge.manager import StrategicKnowledgeBase
from src.core.knowledge.reranker import RerankerService
from src.core.llm.provider import LLMProvider
from src.core.memory import StrategicMemory
from src.core.personas import Personas
from src.core.services.history import HistoryService
from src.core.services.usage import UsageService
from src.core.validator import SemanticValidator
from src.utils.logger import setup_logger

logger = setup_logger("ZenithAgent")


class ZenithAgent:
    """
    The orchestrator for the Zenith autonomous system.

    Coordinates intent analysis, history management, situational memory,
    conditional knowledge retrieval (RAG), and structured quality auditing.
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
        active_model_name: Optional[str] = None,
        mode: str = "byok",
        remaining_quota: Optional[int] = None,
        reranker_override: Optional[RerankerService] = None,
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

        self.knowledge_base = knowledge_base
        self.context_builder = context_builder
        self.analyzer = analyzer
        self.validator = validator
        self.judge = judge
        self.memory = memory

        self.active_model_name = active_model_name or config.MODEL_NAME
        self.mode = mode
        self.remaining_quota = remaining_quota
        self.reranker_override = reranker_override

        self.usage_service = UsageService(self.db)
        self.history_service = HistoryService(self.db)

        self.current_session_id: Optional[str] = None
        self.main_session: Any = None

        logger.debug("ZenithAgent instance initialized via dependency injection.")

    def start_chat(self, session_id: str, user_id: str) -> None:
        """
        Prepares the agent synchronously for a new or existing chat session (CLI).
        """
        self.current_session_id = session_id
        self.db.create_session(session_id, user_id)
        formatted_history = self.history_service.get_formatted_history(
            session_id, user_id
        )
        self.main_session = self.llm.start_chat(history=formatted_history)
        logger.info(
            f"Chat session '{session_id}' started. History restored: {len(formatted_history)} items."
        )

    async def start_chat_async(self, session_id: str, user_id: str) -> None:
        """
        Prepares the agent asynchronously without blocking the event loop.
        """
        self.current_session_id = session_id
        await asyncio.to_thread(self.db.create_session, session_id, user_id)
        formatted_history = await asyncio.to_thread(
            self.history_service.get_formatted_history, session_id, user_id
        )
        self.main_session = self.llm.start_chat(history=formatted_history)
        logger.info(
            f"Chat session '{session_id}' started. History restored: {len(formatted_history)} items."
        )

    async def run_analysis_async(
        self, user_input: str, user_id: str, session_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        The main pipeline for processing user input and emitting typed NDJSON events.
        """
        if self.current_session_id != session_id or not self.main_session:
            await self.start_chat_async(session_id, user_id)

        await self.memory.manage_history(self.main_session, user_id)
        logger.info(f"Analyzing Input (Session: {session_id}): {user_input[:50]}...")

        # 1. Input Shielding
        if not self.validator.validate_user_input(user_input):
            yield {
                "type": "error",
                "content": (
                    "⚠️ **Input Blocked:** Sua mensagem acionou nossos protocolos de "
                    "segurança (chave sensível, cartão ou tentativa de bypass)."
                ),
            }
            return

        # 2. Cognitive Routing + Router Output Validation
        try:
            analysis_result = await self.analyzer.analyze_intent_async(user_input)
            if not self.validator.validate(analysis_result):
                analysis_result = self.analyzer._get_fallback_response(user_input)
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            analysis_result = self.analyzer._get_fallback_response(user_input)

        nature = analysis_result.get("natureza", "Raciocínio")
        complexity = analysis_result.get("complexidade", "Composta")

        # 3. Conditional RAG Gate (skip retrieval and rerank on Simples queries)
        rag_context = ""
        if complexity != "Simples":
            try:
                retrieved = await self.knowledge_base.retrieve_async(
                    user_input, reranker=self.reranker_override
                )
                rag_context = self.context_builder.format_rag_context(retrieved)
            except Exception as e:
                logger.error(f"Knowledge Retrieval failed: {e}")

        # 4. Scoped Memory & Prompt Assembly (static-first order)
        selected_persona = Personas.get_persona(nature)
        system_injection = self.context_builder.build_system_injection(selected_persona)
        memory_context = await asyncio.to_thread(
            self.memory.get_context_injection, user_id
        )

        final_prompt = self.context_builder.assemble_prompt(
            system_injection, memory_context, rag_context, user_input
        )

        # 5. Emit request metadata out-of-band & log user turn
        yield {
            "type": "meta",
            "content": "",
            "metadata": {
                "mode": self.mode,
                "model": self.active_model_name,
                "nature": nature,
                "complexity": complexity,
                "remaining_quota": self.remaining_quota,
            },
        }

        await asyncio.to_thread(
            self.db.log_interaction,
            self.current_session_id,
            user_id,
            "user",
            user_input,
        )

        # 6. Clean Streamed Generation & Intelligent Quality Gate
        full_response_text = ""
        metadata: Dict[str, Any] = {
            "mode": self.mode,
            "model": self.active_model_name,
            "nature": nature,
            "complexity": complexity,
        }

        try:
            stream = self.llm.send_message_async(
                self.main_session, final_prompt, stream=True
            )
            async for chunk in stream:
                if isinstance(chunk, dict) and "usage_metadata" in chunk:
                    await asyncio.to_thread(
                        self.usage_service.log_tokens,
                        user_id,
                        session_id,
                        self.active_model_name,
                        chunk["usage_metadata"],
                    )
                    continue
                if isinstance(chunk, str) and chunk:
                    full_response_text += chunk
                    yield {"type": "chunk", "content": chunk}

            # Intelligent Quality Gate: audit only non-simple responses out-of-band
            if complexity != "Simples" and full_response_text.strip():
                evaluation = await self.judge.evaluate_async(
                    user_input, full_response_text
                )
                score = evaluation.get("score", 85)
                feedback = evaluation.get("feedback", "")
                needs_refinement = bool(evaluation.get("needs_refinement", False))

                metadata["score"] = score
                metadata["judge_feedback"] = feedback
                metadata["needs_refinement"] = needs_refinement

                yield {
                    "type": "quality",
                    "content": "",
                    "metadata": {
                        "score": score,
                        "feedback": feedback,
                        "needs_refinement": needs_refinement,
                    },
                }

            # Background task for isolated per-user memory extraction
            if full_response_text.strip():
                asyncio.create_task(
                    self.memory.extract_entities_async(
                        user_id, user_input, full_response_text
                    )
                )

        except Exception as e:
            logger.critical(f"Agent Pipeline Failure: {e}")
            metadata["status"] = "failed"
            metadata["error_msg"] = str(e)
            yield {
                "type": "error",
                "content": f"Processing unit encountered an internal failure: {str(e)}",
            }
        finally:
            if full_response_text:
                await asyncio.to_thread(
                    self.db.log_interaction,
                    self.current_session_id,
                    user_id,
                    "model",
                    full_response_text,
                    metadata=metadata,
                )
