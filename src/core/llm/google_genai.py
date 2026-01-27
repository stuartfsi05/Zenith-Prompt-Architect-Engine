from typing import AsyncGenerator, Any, Dict, List

import google.generativeai as genai
from google.generativeai import protos

from src.core.llm.provider import LLMProvider
from src.utils.logger import setup_logger

logger = setup_logger("GoogleGenAIProvider")

class GoogleGenAIProvider(LLMProvider):
    """
    Implementation of LLMProvider for Google Gemini Models.
    """

    def __init__(self, model_name: str, temperature: float = 0.1, system_instruction: str = None):
        self.model_name = model_name
        self.generation_config = {
            "temperature": temperature,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
        }
        self.system_instruction = system_instruction
        self.model = None

    def configure(self, api_key: str):
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=self.generation_config,
                system_instruction=self.system_instruction,
                tools=[protos.Tool(google_search={})],
            )
            logger.info(f"Initialized Google GenAI Model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to configure Google GenAI: {e}")
            raise

    def start_chat(self, history: List[Dict[str, Any]] = None) -> Any:
        if not self.model:
            raise RuntimeError("Model not configured. Call configure() first.")
        
        # Convert generic history format to Google's format if necessary
        # Assuming history comes in [{"role": "user", "parts": ["text"]}] format which matches closely
        return self.model.start_chat(history=history or [])

    async def generate_content_async(self, prompt: str, **kwargs) -> str:
        if not self.model:
            raise RuntimeError("Model not configured.")
        
        response = await self.model.generate_content_async(prompt, **kwargs)
        return response.text

    async def send_message_async(self, session: Any, message: str, stream: bool = False) -> AsyncGenerator[str, None]:
        if not session:
            raise ValueError("Session cannot be None.")
        
        response = await session.send_message_async(message, stream=stream)
        
        if stream:
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        else:
            yield response.text
