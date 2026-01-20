import google.generativeai as genai
from google.generativeai import protos
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from src.core.config import Config
from src.utils.logger import setup_logger
from src.core.analyzer import StrategicAnalyzer
from src.core.validator import SemanticValidator
from src.core.judge import TheJudge
from src.core.knowledge import StrategicKnowledgeBase
from src.core.personas import Personas

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
        self.analyzer = StrategicAnalyzer()
        self.validator = SemanticValidator()
        self.judge = TheJudge()
        self.knowledge_base = StrategicKnowledgeBase(self.config)

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
        self.main_session = self.model.start_chat()

    def _configure_genai(self):
        genai.configure(api_key=self.config.GOOGLE_API_KEY)

    def start_chat(self):
        """Optional: Resets the session if needed."""
        logger.info("Session Reset.")
        self.main_session = self.model.start_chat()

    def _prune_history(self):
        """
        Sliding Window Mechanism.
        Maintains only the last 20 turns to prevent Context Window Overflow.
        """
        MAX_HISTORY = 20
        if len(self.main_session.history) > MAX_HISTORY:
            logger.info(
                f"🧹 Pruning History (Current: {len(self.main_session.history)}). Keeping last {MAX_HISTORY}."
            )
            self.main_session.history = self.main_session.history[-MAX_HISTORY:]

    def run_analysis(self, user_input: str) -> str:
        """
        Executes the SOTA Protocol:
        Analysis -> Dynamic Prompt Injection -> Hybrid Retrieval -> Thought Process -> Execution -> Self-Correction.
        """
        self._prune_history()  # Sliding Window Cleanup

        logger.info(f"Processing Input: {user_input[:50]}...")

        # 0. Safety Check (Input Guardrail)
        if not self.validator.validate_user_input(user_input):
            return "⚠️ Input blocked by Safety Protocols."

        # 1. Strategic Analysis (Cognitive Router)
        analysis_result = self.analyzer.analyze_intent(user_input)
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

        # 3. Hybrid RAG Retrieval (SOTA)
        rag_context = ""
        if complexity != "Simples":
            rag_context = self.knowledge_base.retrieve(user_input)

        final_prompt = f"{system_injection}\n\n"

        if rag_context:
            final_prompt += (
                f"--- [RELEVANT CONTEXT (Hybrid Search)] ---\n{rag_context}\n\n"
            )

        final_prompt += f"--- [USER REQUEST] ---\n{user_input}"

        # 4. Execution (Persistent Session)
        try:
            # Initial Call
            logger.info("Executing SOTA Inference with Structured CoT...")
            response = self.main_session.send_message(final_prompt)
            response_text = response.text

            # 5. Self-Healing Loop (Reflexion Pattern)
            MIN_SCORE_THRESHOLD = 80
            MAX_RETRIES = 2
            attempt = 0

            while attempt <= MAX_RETRIES:
                # 5.1. Evaluate (The Judge)
                evaluation = self.judge.evaluate(user_input, response_text)
                score = evaluation.get("score", 0)
                feedback = evaluation.get("feedback", "")
                needs_refinement = evaluation.get("needs_refinement", False)

                logger.info(
                    f"Reflexion (Att {attempt}): Score={score} | Needs Refinement={needs_refinement}"
                )

                # 5.2. Success Condition
                if score >= MIN_SCORE_THRESHOLD and not needs_refinement:
                    return response_text

                # 5.3. Retry Limit
                if attempt >= MAX_RETRIES:
                    logger.warning(f"❌ Max retries reached ({score}).")
                    return f"⚠️ [SOTA Warning: Low Confidence (Score {score})]\n{response_text}"

                # 5.4. Refinement Prompt
                logger.warning(f"⚠️ Triggering Self-Correction. Feedback: {feedback}")
                refinement_prompt = (
                    f"--- [SELF-CORRECTION PROTOCOL] ---\n"
                    f"Analyze your previous response. The Quality Judge rejected it (Score: {score}).\n"
                    f"CRITICAL FEEDBACK: {feedback}\n"
                    f"TASK: Rewrite the response leveraging your <thinking> process to fix these errors."
                )

                response = self.main_session.send_message(refinement_prompt)
                response_text = response.text
                attempt += 1

            return response_text

        except Exception as e:
            logger.error(f"SOTA Execution Error: {e}")
            return f"⚠️ **System Error**: {str(e)}"
