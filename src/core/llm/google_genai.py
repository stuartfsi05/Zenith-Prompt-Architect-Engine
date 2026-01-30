from typing import Any, AsyncGenerator, Dict, List
import asyncio

from google import genai
from google.genai import types

from src.core.llm.provider import LLMProvider
from src.utils.logger import setup_logger

logger = setup_logger("GoogleGenAIProvider")


class GoogleGenAIProvider(LLMProvider):
    """
    Implementation of LLMProvider for Google Gemini Models using google-genai SDK (v1.0+).
    """

    def __init__(
        self, model_name: str, temperature: float = 0.1, system_instruction: str = None
    ):
        self.model_name = model_name
        self.default_config = {
            "temperature": temperature,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
        }
        self.system_instruction = system_instruction
        self.client = None

    def configure(self, api_key: str):
        try:
            self.client = genai.Client(api_key=api_key)
            logger.info(f"Initialized Google GenAI Client: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to configure Google GenAI: {e}")
            raise

    def start_chat(self, history: List[Dict[str, Any]] = None) -> Any:
        """
        Creates and returns a coroutine for creating an async chat session.
        The caller must await this coroutine to get the actual chat object.
        """
        if not self.client:
            raise RuntimeError("Client not configured. Call configure() first.")

        # Convert history if needed
        formatted_history = []
        if history:
            for item in history:
                formatted_history.append(
                    types.Content(
                        role=item["role"],
                        parts=[types.Part.from_text(text=p) for p in item["parts"]]
                    )
                )

        # Return the async chat creation - caller must await this
        return self.client.aio.chats.create(
            model=self.model_name,
            history=formatted_history,
            config=types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=self.default_config["temperature"],
            )
        )

    async def generate_content_async(self, prompt: str, **kwargs) -> str:
        """
        Generates content.
        NOTE: Callers using 'generation_config' must switch to 'config' or we map it here.
        To be safe, we map 'generation_config' to 'config' if present.
        """
        if not self.client:
            raise RuntimeError("Client not configured.")
        
        # Mapping legacy generation_config to config
        config = kwargs.pop("config", None)
        legacy_config = kwargs.pop("generation_config", None)
        
        final_config = config
        if legacy_config and not final_config:
            # Simple mapping or pass as is if dict
            final_config = legacy_config
            
        # Merge defaults if needed, but for now specific overrides win
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=final_config,
            **kwargs
        )
        return response.text

    async def send_message_async(
        self, session: Any, message: str, stream: bool = False
    ) -> AsyncGenerator[str, None]:
        if not session:
            raise ValueError("Session cannot be None.")

        # session is now an AsyncChat object from client.aio.chats.create()
        if stream:
            # send_message_stream for async chat returns an awaitable async iterator
            response_stream = await session.send_message_stream(message)
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        else:
            response = await session.send_message(message)
            yield response.text
