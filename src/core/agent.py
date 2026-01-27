import asyncio

from src.core.analyzer import StrategicAnalyzer
from src.core.config import Config
from src.core.database import DatabaseManager
from src.core.judge import TheJudge
from src.core.knowledge.manager import StrategicKnowledgeBase
from src.core.llm.google_genai import GoogleGenAIProvider
from src.core.memory import StrategicMemory
from src.core.personas import Personas
from src.core.validator import SemanticValidator
from src.utils.logger import setup_logger

logger = setup_logger("ZenithAgent")


class ZenithAgent:
    """
    Main agent class that coordinates analysis, memory, knowledge retrieval,
    and response generation.
    """

    def __init__(self, config: Config, system_instruction: str):
        self.config = config
        self.default_system_instruction = system_instruction

        self.analyzer = StrategicAnalyzer(self.config)
        self.validator = SemanticValidator()
        self.judge = TheJudge(self.config)
        self.knowledge_base = StrategicKnowledgeBase(self.config)
        self.memory = StrategicMemory(self.config)
        self.db = DatabaseManager(self.config)

        logger.info(f"Initializing Engine: {self.config.MODEL_NAME}")
        
        # Initialize LLM Provider
        self.llm = GoogleGenAIProvider(
            model_name=self.config.MODEL_NAME,
            temperature=self.config.TEMPERATURE,
            system_instruction=self.default_system_instruction
        )
        self.llm.configure(self.config.GOOGLE_API_KEY)

        self.current_session_id = "default_session"
        self.db.create_session(self.current_session_id)
        self.main_session = None

    def start_chat(self, session_id: str = "default_session"):
        """
        Starts the chat session and loads history from the database.
        """
        self.current_session_id = session_id
        logger.info(f"Loading Session: {session_id}")

        db_history = self.db.get_history(session_id)

        formatted_history = []
        for turn in db_history:
            formatted_history.append({
                "role": turn["role"],
                "parts": turn["parts"]
            })

        # Use LLM Provider to start chat
        self.main_session = self.llm.start_chat(history=formatted_history)
        logger.info(f"Context Restored ({len(formatted_history)} items).")

    def _prune_history(self):
        """
        Prunes history if it exceeds the maximum length.
        Oldest messages are sent to memory consolidation.
        """
        max_history = 20
        history_len = len(self.main_session.history)

        if history_len > max_history:
            prune_count = history_len - max_history
            items_to_prune = self.main_session.history[:prune_count]

            logger.info(
                f"Pruning History (Current: {history_len}). "
                f"Archiving {len(items_to_prune)} items."
            )

            asyncio.create_task(
                self.memory.consolidate_memory_async(items_to_prune)
            )

            self.main_session.history = self.main_session.history[prune_count:]

    async def run_analysis_async(self, user_input: str):
        """
        Process user input through analysis, retrieval, and generation steps.
        """
        self._prune_history()

        logger.info(f"Processing Input: {user_input[:50]}...")

        if not self.validator.validate_user_input(user_input):
            yield "⚠️ Input blocked by Safety Protocols."
            return

        # Start analysis and retrieval concurrently
        analyzer_task = asyncio.create_task(
            self.analyzer.analyze_intent_async(user_input)
        )
        knowledge_task = asyncio.create_task(
            self.knowledge_base.retrieve_async(user_input)
        )

        try:
            analysis_result = await analyzer_task
        except Exception as e:
            logger.error(f"Analyzer failed: {e}")
            analysis_result = self.analyzer._get_fallback_response(user_input)

        nature = analysis_result.get("natureza", "Raciocínio")
        complexity = analysis_result.get("complexidade", "Composta")

        logger.info(f"Router: Nature={nature} | Complexity={complexity}")

        if not self.validator.validate(analysis_result):
            logger.warning("Router validation failed. Proceeding with caution.")

        selected_persona = Personas.get_persona(nature)

        system_injection = (
            f"--- [SYSTEM OVERRIDE: ACTIVE PERSONA] ---\n"
            f"{selected_persona}\n\n"
            f"--- [MANDATORY INSTRUCTION: DEEP THINKING] ---\n"
            f"Antes de responder, você DEVE analisar o pedido passo a passo "
            f"dentro de tags <thinking>...</thinking>.\n"
            f"Planeje sua resposta, verifique fatos e critique sua própria "
            f"lógica.\n"
            f"Apenas após o fechamento da tag </thinking>, forneça a resposta "
            f"final ao usuário.\n"
        )

        rag_context = ""
        if complexity != "Simples":
            try:
                rag_context = await knowledge_task
            except Exception as e:
                logger.error(f"Knowledge Retrieval failed: {e}")
                rag_context = ""
        else:
            try:
                await knowledge_task
            except Exception:
                pass

        final_prompt = f"{system_injection}\n\n"

        memory_context = self.memory.get_context_injection()
        if memory_context:
            final_prompt += f"{memory_context}\n"

        if rag_context:
            final_prompt += (
                f"--- [RELEVANT CONTEXT (Hybrid Search)] ---\n"
                f"{rag_context}\n\n"
            )

        final_prompt += f"--- [USER REQUEST] ---\n{user_input}"

        self.db.log_interaction(self.current_session_id, "user", user_input)

        full_response_text = ""
        metadata = {}

        try:
            stream = self.llm.send_message_async(
                self.main_session, final_prompt, stream=True
            )

            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
                    full_response_text += chunk.text

            # Self-correction / Judgement logic
            min_score_threshold = 80
            max_retries = 2
            attempt = 0

            evaluation = await self.judge.evaluate_async(
                user_input, full_response_text
            )
            score = evaluation.get("score", 0)
            feedback = evaluation.get("feedback", "")
            needs_refinement = evaluation.get("needs_refinement", False)

            metadata["score"] = score
            metadata["feedback"] = feedback
            metadata["refinement_attempts"] = 0

            if score < min_score_threshold or needs_refinement:
                logger.warning(
                    f"Triggering Self-Correction. Score: {score}. "
                    f"Feedback: {feedback}"
                )

                yield (
                    f"\n\n[dim]⚠️ Quality Assurance detected issues "
                    f"(Score: {score}). Refining...[/dim]\n\n"
                )

                while attempt < max_retries:
                    refinement_prompt = (
                        f"--- [SELF-CORRECTION PROTOCOL] ---\n"
                        f"Analyze your previous response. The Quality Judge "
                        f"rejected it (Score: {score}).\n"
                        f"CRITICAL FEEDBACK: {feedback}\n"
                        f"TASK: Rewrite the response leveraging your <thinking> "
                        f"process to fix these errors. Keep it concise."
                    )

                    response_stream = self.llm.send_message_async(
                        self.main_session, refinement_prompt, stream=True
                    )

                    full_response_text = ""
                    async for chunk in response_stream:
                        if chunk.text:
                            yield chunk.text
                            full_response_text += chunk.text

                    attempt += 1
                    metadata["refinement_attempts"] = attempt

                    evaluation = await self.judge.evaluate_async(
                        user_input, full_response_text
                    )
                    score = evaluation.get("score", 0)
                    metadata["score"] = score

                    if score >= min_score_threshold:
                        break

                    feedback = evaluation.get("feedback", "")

            asyncio.create_task(
                self.memory.extract_entities_async(
                    user_input, full_response_text
                )
            )

        except (ValueError, KeyError) as e:
            logger.error(f"Validation/Data Error: {e}")
            yield f"\n⚠️ **Data Error**: {str(e)}"
            metadata["error"] = str(e)
            
        except RuntimeError as e:
            logger.error(f"Runtime System Error: {e}")
            yield f"\n⚠️ **System Error**: {str(e)}"
            metadata["error"] = str(e)
            
        except Exception as e:
            logger.critical(f"Critical Unexpected Error: {e}")
            yield f"\n⚠️ **Critical Failure**: Please contact support. ({str(e)})"
            metadata["error"] = str(e)

        finally:
            if full_response_text:
                self.db.log_interaction(
                    self.current_session_id,
                    "model",
                    full_response_text,
                    metadata=metadata
                )
