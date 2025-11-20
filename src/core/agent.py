import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from typing import Dict, Any
from src.core.config import Config
from src.utils.logger import setup_logger
from src.core.analyzer import StrategicAnalyzer
from src.core.validator import SemanticValidator
from src.core.judge import TheJudge

logger = setup_logger("ZenithAgent")

class ZenithAgent:
    """
    The Zenith Orchestrator.
    Manages the lifecycle: Analysis -> Validation -> Execution (LLM) -> Evaluation.
    """

    def __init__(self, config: Config, system_instruction: str):
        self.config = config
        self.system_instruction = system_instruction
        self.chat_session = None
        
        # Initialize Sub-Modules (The Architecture)
        self.analyzer = StrategicAnalyzer()
        self.validator = SemanticValidator()
        self.judge = TheJudge()

        self._configure_genai()
        self.model = self._initialize_model()

    def _configure_genai(self):
        genai.configure(api_key=self.config.GOOGLE_API_KEY)

    def _initialize_model(self) -> genai.GenerativeModel:
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

        logger.info(f"Initializing model: {self.config.MODEL_NAME}")
        return genai.GenerativeModel(
            model_name=self.config.MODEL_NAME,
            safety_settings=safety_settings,
            generation_config=generation_config,
            system_instruction=self.system_instruction
        )

    def start_chat(self):
        logger.info("Starting new chat session.")
        self.chat_session = self.model.start_chat(history=[])

    def run_analysis(self, user_input: str) -> str:
        """
        Executes the Full Zenith Protocol (Analysis -> Validation -> Execution).
        """
        if not self.chat_session:
            self.start_chat()

        # 1. Strategic Analysis
        strategy = self.analyzer.analyze_intent(user_input)
        
        # 2. Semantic Validation
        if self.validator.validate(strategy):
            logger.info("Validation Passed. Proceeding to Inference.")

        # 3. Execution (The actual LLM call)
        logger.info("Sending message to Gemini API...")
        try:
            response = self.chat_session.send_message(user_input)
            logger.info("Response received successfully.")
            
            # 4. Self-Evaluation (The Judge) - Post-processing
            # In a real scenario, we would critique the response here.
            # For the dummy, we just log that it happened.
            self.judge.evaluate(user_input, response.text)
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error during API call: {e}")
            return f"⚠️ **System Error**: {str(e)}"