import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from src.core.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("ZenithAgent")

class ZenithAgent:
    """
    The core agent class that orchestrates interactions with the Gemini API.
    """

    def __init__(self, config: Config, system_instruction: str):
        """
        Initializes the ZenithAgent.

        Args:
            config (Config): Configuration object containing API keys and settings.
            system_instruction (str): The system prompt to guide the agent's behavior.
        """
        self.config = config
        self.system_instruction = system_instruction
        self._chat_session = None

        self._configure_genai()
        self._model = self._initialize_model()

    def _configure_genai(self):
        """Configures the Google Generative AI library."""
        genai.configure(api_key=self.config.GOOGLE_API_KEY)

    def _initialize_model(self) -> genai.GenerativeModel:
        """
        Initializes the GenerativeModel with safety settings and generation config.

        Returns:
            genai.GenerativeModel: The configured Gemini model.
        """
        generation_config = {
            "temperature": self.config.TEMPERATURE,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }

        # Safety settings - Adjust as needed for the specific use case
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

        logger.info(f"Initializing model: {self.config.MODEL_NAME}")
        return genai.GenerativeModel(
            model_name=self.config.MODEL_NAME,
            safety_settings=safety_settings,
            generation_config=generation_config,
            system_instruction=self.system_instruction
        )

    def start_chat(self):
        """Starts a new chat session."""
        logger.info("Starting new chat session.")
        self._chat_session = self._model.start_chat(history=[])

    def run_analysis(self, user_input: str) -> str:
        """
        Sends a message to the agent and returns the response.

        Args:
            user_input (str): The user's input message.

        Returns:
            str: The agent's response text.
        """
        if not self._chat_session:
            self.start_chat()

        logger.info("Sending message to Gemini API...")
        try:
            response = self._chat_session.send_message(user_input)
            logger.info("Response received successfully.")
            return response.text
        except Exception as e:
            logger.error(f"Error during API call: {e}")
            return f"⚠️ **System Error**: An error occurred while processing your request.\n\n`{str(e)}`"
