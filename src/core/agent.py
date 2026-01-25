import google.generativeai as genai
from google.generativeai import protos
from google.generativeai.types import HarmBlockThreshold, HarmCategory
import asyncio

from src.core.analyzer import StrategicAnalyzer
from src.core.config import Config
from src.core.database import DatabaseManager
from src.core.judge import TheJudge
from src.core.knowledge import StrategicKnowledgeBase
from src.core.memory import StrategicMemory
from src.core.personas import Personas
from src.core.validator import SemanticValidator
from src.utils.logger import setup_logger

logger = setup_logger("ZenithAgent")


class ZenithAgent:
    """
    The Zenith Orchestrator (Polymorphic Engine - SOTA Architecture).
    Features: Single Persistent Session, Dynamic Persona Injection, Structured CoT, Hybrid RAG.
    """

    def __init__(self, config: Config, system_instruction: str):
        self.config = config
        self.default_system_instruction = system_instruction

        # Initialize Sub-Modules (The Architecture)
        # Initialize Sub-Modules (The Architecture)
        self.analyzer = StrategicAnalyzer(self.config)
        self.validator = SemanticValidator()
        self.judge = TheJudge(self.config)
        self.knowledge_base = StrategicKnowledgeBase(self.config)
        self.memory = StrategicMemory(self.config)
        self.db = DatabaseManager(self.config)

        self._configure_genai()

        # SOTA: Single Persistent Model with Tools Enabled
        logger.info(
            f"Initializing SOTA Engine: {self.config.MODEL_NAME} [Tools: Search]"
        )
        self.model = genai.GenerativeModel(
            model_name=self.config.MODEL_NAME,
            generation_config={
                "temperature": self.config.TEMPERATURE,
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": 8192,
            },
            system_instruction=self.default_system_instruction,
            tools=[protos.Tool(google_search={})],
        )

        # Persistent Session (Context Caching & Long Memory)
        self.current_session_id = "default_session"
        self.db.create_session(self.current_session_id)
        # self.start_chat(self.current_session_id)  <-- Removed to avoid double init (called in main.py)

    def _configure_genai(self):
        genai.configure(api_key=self.config.GOOGLE_API_KEY)

    def start_chat(self, session_id: str = "default_session"):
        """
        Starts the chat session.
        Loads history from SQLite to ensure Continuity of Self.
        """
        self.current_session_id = session_id
        logger.info(f"🔄 Loading Session: {session_id}")
        
        # Load from DB
        db_history = self.db.get_history(session_id)
        
        # Convert to Google GenAI format if needed (list of Content objects)
        # Using raw history injection for now or simple list of dicts if library supports it
        # The library expects [{'role': 'user', 'parts': ['text']}, ...]
        
        formatted_history = []
        for turn in db_history:
            formatted_history.append({
                "role": turn["role"],
                "parts": turn["parts"]
            })
            
        self.main_session = self.model.start_chat(history=formatted_history)
        logger.info(f"✅ Context Restored ({len(formatted_history)} items).")

    def _prune_history(self):
        """
        Sliding Window Mechanism with Semantic Compression (Smart Pruning).
        1. Checks if history > MAX_HISTORY.
        2. Slices off the oldest messages.
        3. Sends them to the Memory Module for consolidation (Async).
        """
        MAX_HISTORY = 20
        history_len = len(self.main_session.history)
        
        if history_len > MAX_HISTORY:
            prune_count = history_len - MAX_HISTORY
            # Ensure we count pairs (User+Model) if possible, but genai logic handles it.
            # We take the oldest 'prune_count' messages.
            
            items_to_prune = self.main_session.history[:prune_count]
            
            logger.info(
                f"🧹 Pruning History (Current: {history_len}). Archiving {len(items_to_prune)} items."
            )
            
            # Fire-and-forget async task for memory consolidation
            # We don't await this because pruning must be instant for the current turn.
            asyncio.create_task(self.memory.consolidate_memory_async(items_to_prune))
            
            # Actually remove from history
            self.main_session.history = self.main_session.history[prune_count:]

    async def run_analysis_async(self, user_input: str):
        """
        Executes the SOTA Protocol (Async Generator):
        Analysis -> Dynamic Prompt Injection -> Hybrid Retrieval -> Thought Process -> Execution -> Self-Correction.
        Feature: Streaming Response & Speculative Parallelism.
        """
        self._prune_history()  # Sliding Window Cleanup

        logger.info(f"Processing Input: {user_input[:50]}...")

        # 0. Safety Check (Input Guardrail)
        if not self.validator.validate_user_input(user_input):
            yield "⚠️ Input blocked by Safety Protocols."
            return

        # 1. Speculative Parallelism: Run Analyzer and Knowledge Retrieval concurrently
        # We start both tasks immediately.
        import asyncio

        logger.info("🚀 Launching Speculative Parallelism (Analyzer + RAG)...")
        analyzer_task = asyncio.create_task(self.analyzer.analyze_intent_async(user_input))
        
        # We start retrieval immediately, even before knowing complexity.
        # If complexity ends up being "Simple", we might discard the result or just not use it,
        # but this ensures zero-latency for complex queries.
        knowledge_task = asyncio.create_task(self.knowledge_base.retrieve_async(user_input))

        # Await Analyzer first to determine strategy
        try:
            analysis_result = await analyzer_task
        except Exception as e:
            logger.error(f"Analyzer failed: {e}")
            analysis_result = self.analyzer._get_fallback_response(user_input)

        nature = analysis_result.get("natureza", "Raciocínio")
        complexity = analysis_result.get("complexidade", "Composta")

        logger.info(f"Router: Nature={nature} | Complexity={complexity}")

        # 1.1 Structural Validation
        if not self.validator.validate(analysis_result):
            logger.warning("Router validation failed. Proceeding with caution.")

        # 2. Dynamic Persona Injection & Thinking Enforcement (Structured CoT)
        selected_persona = Personas.get_persona(nature)

        system_injection = (
            f"--- [SYSTEM OVERRIDE: ACTIVE PERSONA] ---\n"
            f"{selected_persona}\n\n"
            f"--- [MANDATORY INSTRUCTION: DEEP THINKING] ---\n"
            f"Antes de responder, você DEVE analisar o pedido passo a passo dentro de tags <thinking>...</thinking>.\n"
            f"Planeje sua resposta, verifique fatos e critique sua própria lógica.\n"
            f"Apenas após o fechamento da tag </thinking>, forneça a resposta final ao usuário.\n"
        )

        # 3. Hybrid RAG Retrieval (SOTA) - Await the result of the speculative task
        rag_context = ""
        # Only use RAG if complexity is not Simples, but we already launched the task.
        # If we don't need it, we just ignore the result (or cancel the task if we want to save resources, but completion is safer).
        if complexity != "Simples":
            try:
                rag_context = await knowledge_task
            except Exception as e:
                logger.error(f"Knowledge Retrieval failed: {e}")
                rag_context = ""
        else:
            # If simple, we don't need the RAG result, but we should ensure the background task cleans up
            # However, awaiting it is cleaner to avoid detached task warnings, or we can just let it finish.
            # For this focused implementation without task management overhead, let's just await it and discard.
            try:
                await knowledge_task
            except:
                pass

        final_prompt = f"{system_injection}\n\n"

        # Inject Progressive Semantic Memory (Master Summary + User Profile)
        memory_context = self.memory.get_context_injection()
        if memory_context:
            final_prompt += f"{memory_context}\n"

        if rag_context:
            final_prompt += (
                f"--- [RELEVANT CONTEXT (Hybrid Search)] ---\n{rag_context}\n\n"
            )

        final_prompt += f"--- [USER REQUEST] ---\n{user_input}"
        
        # LOG USER INTERACTION
        self.db.log_interaction(self.current_session_id, "user", user_input)

        # 4. Execution (Persistent Session) with Streaming
        full_response_text = ""
        metadata = {}
        
        try:
            logger.info("Executing SOTA Inference with Streaming...")
            
            # Streaming Generate
            stream = await self.main_session.send_message_async(final_prompt, stream=True)
            
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
                    full_response_text += chunk.text

            # 5. Self-Healing Loop (Reflexion Pattern) - Post-Stream Verification
            
            MIN_SCORE_THRESHOLD = 80
            MAX_RETRIES = 2 
            attempt = 0

            # First evaluation
            evaluation = await self.judge.evaluate_async(user_input, full_response_text)
            score = evaluation.get("score", 0)
            feedback = evaluation.get("feedback", "")
            needs_refinement = evaluation.get("needs_refinement", False)

            # Metadata for Analytics
            metadata["score"] = score
            metadata["feedback"] = feedback
            metadata["refinement_attempts"] = 0

            if score < MIN_SCORE_THRESHOLD or needs_refinement:
                logger.warning(f"⚠️ Triggering Self-Correction. Score: {score}. Feedback: {feedback}")
                
                yield f"\n\n[dim]⚠️ Auditoria de Qualidade detectou falhas (Score: {score}). Refinando...[/dim]\n\n"

                while attempt < MAX_RETRIES:
                     refinement_prompt = (
                        f"--- [SELF-CORRECTION PROTOCOL] ---\n"
                        f"Analyze your previous response. The Quality Judge rejected it (Score: {score}).\n"
                        f"CRITICAL FEEDBACK: {feedback}\n"
                        f"TASK: Rewrite the response leveraging your <thinking> process to fix these errors. Keep it concise."
                    )
                     
                     response = await self.main_session.send_message_async(refinement_prompt, stream=True)
                     
                     full_response_text = "" # Reset for new capture
                     async for chunk in response:
                         if chunk.text:
                             yield chunk.text
                             full_response_text += chunk.text
                     
                     attempt += 1
                     metadata["refinement_attempts"] = attempt
                     
                     evaluation = await self.judge.evaluate_async(user_input, full_response_text)
                     score = evaluation.get("score", 0)
                     metadata["score"] = score # Update final score
                     
                     if score >= MIN_SCORE_THRESHOLD:
                         break 
                     
                     feedback = evaluation.get("feedback", "")
            
                     evaluation = await self.judge.evaluate_async(user_input, full_response_text)
                     score = evaluation.get("score", 0)
                     metadata["score"] = score # Update final score
                     
                     if score >= MIN_SCORE_THRESHOLD:
                         break 
                     
                     feedback = evaluation.get("feedback", "")
            
            # 6. Memory Extraction (Async Background Task)
            asyncio.create_task(self.memory.extract_entities_async(user_input, full_response_text))

        except Exception as e:
            logger.error(f"SOTA Execution Error: {e}")
            yield f"\n⚠️ **System Error**: {str(e)}"
            metadata["error"] = str(e)
        
        finally:
            # LOG MODEL INTERACTION (Guaranteed)
            if full_response_text:
                self.db.log_interaction(
                    self.current_session_id, 
                    "model", 
                    full_response_text, 
                    metadata=metadata
                )
