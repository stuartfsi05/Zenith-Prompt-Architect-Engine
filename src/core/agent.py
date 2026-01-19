import google.generativeai as genai
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
    The Zenith Orchestrator (Polymorphic Engine).
    Manages the lifecycle: Analysis -> Persona Selection -> Validation -> Execution -> Evaluation.
    """

    def __init__(self, config: Config, system_instruction: str):
        self.config = config
        self.default_system_instruction = system_instruction
        self.chat_session = None

        # Initialize Sub-Modules (The Architecture)
        self.analyzer = StrategicAnalyzer()
        self.validator = SemanticValidator()
        self.judge = TheJudge()
        self.knowledge_base = StrategicKnowledgeBase(self.config)

        self._configure_genai()
        # Model is now instantiated dynamically per turn or lazy-loaded, 
        # but we can keep a default one if needed. 
        # For Polymorphic Pattern, we will instantiate inside execution or maintain a cache.
        self.active_model = None 

    def _configure_genai(self):
        genai.configure(api_key=self.config.GOOGLE_API_KEY)

    def _get_model_config(self, tools_enabled: bool = False):
        """Returns the generation config and safety settings."""
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

        generation_config = {
            "temperature": self.config.TEMPERATURE,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        
        return safety_settings, generation_config

    def _instantiate_runtime_model(self, system_instruction: str, enable_search: bool = False) -> genai.GenerativeModel:
        """
        Instantiates a fresh model with specific persona and tools.
        """
        safety_settings, generation_config = self._get_model_config()
        
        tools = "google_search_retrieval" if enable_search else None
        
        # Enforce Strict Grounding Rules only if NOT searching (or adjust as needed)
        # For this implementation, we append grounding if NOT searching to force internal knowledge reliance,
        # unless it's the specific Researcher persona which needs search.
        
        final_instruction = system_instruction
        if not enable_search:
             # Basic grounding for non-search modes if needed, or rely on Persona
             pass

        logger.info(f"Instantiating Runtime Model: {self.config.MODEL_NAME} | Search: {enable_search}")
        
        return genai.GenerativeModel(
            model_name=self.config.MODEL_NAME,
            safety_settings=safety_settings,
            generation_config=generation_config,
            system_instruction=final_instruction,
            tools=tools
        )

    def start_chat(self):
        # In polymorphic mode, 'starting chat' might just be a formality 
        # or initializing a default state.
        logger.info("Initializing Default Session.")
        pass

    def run_analysis(self, user_input: str) -> str:
        """
        Executes the Full Zenith Protocol with Polymorphic Adaptation.
        (Analysis -> Polymorphing -> Validation -> Execution).
        """
        logger.info(f"Processing User Input: {user_input[:50]}...")

        # 1. Strategic Analysis (Cognitive Router)
        analysis_result = self.analyzer.analyze_intent(user_input)
        
        nature = analysis_result.get("natureza", "Raciocínio")
        complexity = analysis_result.get("complexidade", "Composta")
        intent_synthesized = analysis_result.get("intencao_sintetizada", "")
        
        logger.info(f"Cognitive Router Decision: Nature={nature}, Complexity={complexity}")

        # 2. Polymorphic Adaptation (Select Persona & Tools)
        # Get the correct persona text
        selected_persona = Personas.get_persona(nature)
        
        # Determine strict tool usage
        # [I] Investigação -> Enable Search
        # Others -> Disable Search (Performance & Focus)
        is_investigation = "Investigação" in nature or nature.startswith("I")
        
        # Instantiate the specialized agent for this turn
        runtime_model = self._instantiate_runtime_model(
            system_instruction=selected_persona, 
            enable_search=is_investigation
        )
        
        # Start a transient chat for this interaction (or maintain history if needed)
        # For a truly agentic flow, we usually want history. 
        # But switching personas mid-chat can be confusing for the model context.
        # We will create a new chat context for this execution to ensure persona adherence.
        # (Alternatively, we could append history, but let's stick to the requested pattern).
        session = runtime_model.start_chat(history=[])

        # 3. Semantic Validation (Guardrails)
        # We validate the strategy, not necessarily the prompt yet.
        if self.validator.validate(analysis_result):
            logger.info("Validation Passed. Proceeding to Inference.")

        # 4. Execution (The actual LLM call)
        logger.info("Sending message to Polymorphic Zenith...")

        # RAG Integration (Strategic Knowledge Base)
        # Only use RAG if NOT purely code or if explicitly needed. 
        # For simplicity, we apply RAG generally unless it's a very simple task.
        rag_context = ""
        if complexity != "Simples":
            rag_context = self.knowledge_base.retrieve(user_input)
            
        if rag_context:
            logger.info("Enriching prompt with RAG context.")
            final_prompt = f"CONTEXTO DE APOIO (KNOWLEDGE BASE):\n{rag_context}\n\n---\n\nINPUT DO USUÁRIO:\n{user_input}\n\n---\n\nINSTRUÇÃO ADICIONAL DO ROTEADOR:\nIntenção: {intent_synthesized}"
        else:
            final_prompt = user_input

        try:
            response = session.send_message(final_prompt)
            logger.info("Response received successfully.")

            # 5. Self-Evaluation (The Judge) - Post-processing
            self.judge.evaluate(user_input, response.text)

            return response.text

        except Exception as e:
            logger.error(f"Error during API call: {e}")
            return f"⚠️ **Polymorphic Execution Error**: {str(e)}"
