from typing import Any, AsyncGenerator, Dict, List, Optional

from google import genai
from google.genai import types

from src.core.llm.provider import ChatSession, LLMProvider
from src.utils.logger import setup_logger

logger = setup_logger("GoogleGenAIProvider")


def is_modern_gemini_model(model_name: str) -> bool:
    """Returns True for Gemini 3+/4+ models where legacy sampling params are deprecated."""
    normalized = model_name.removeprefix("models/").lower()
    return normalized.startswith(("gemini-3", "gemini-4"))


class GoogleChatSession(ChatSession):
    """
    Wrapper for Google GenAI AsyncChat session.
    Adapts Google's specific history management to the generic ChatSession interface.
    """

    def __init__(self, raw_session: Any):
        self._session = raw_session

    @property
    def history(self) -> List[Any]:
        # Google stores history in self._session._curated_history or .history
        # Accessing private attribute as per original implementation requirement
        if hasattr(self._session, "_curated_history"):
            return self._session._curated_history
        return self._session.history

    @history.setter
    def history(self, value: List[Any]):
        # Google SDK allows setting history directly on the object in some versions,
        # or we manipulate the list.
        if hasattr(self._session, "_curated_history"):
            self._session._curated_history = value
        else:
            # Fallback if internal API changes, though less likely to work for pruning
            self._session.history = value

    async def send_message_async(self, message: str) -> Any:
        # Direct delegation
        return await self._session.send_message(message)


class GoogleGenAIProvider(LLMProvider):
    """
    Implementation of LLMProvider for Google Gemini Models using google-genai SDK (v1.0+).
    """

    def __init__(
        self,
        model_name: str,
        temperature: float = 0.1,
        system_instruction: Optional[str] = None,
        thinking_level: Optional[str] = None,
    ):
        self.model_name = model_name
        self.default_config = {
            "temperature": temperature,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
        }
        self.system_instruction = system_instruction
        self.thinking_level = thinking_level
        self.client = None

    def _build_generate_config(
        self, overrides: Any = None
    ) -> types.GenerateContentConfig:
        """Builds a GenerateContentConfig adapted to the target Gemini generation."""
        if isinstance(overrides, types.GenerateContentConfig):
            config_dict = overrides.model_dump(exclude_none=True)
        elif isinstance(overrides, dict):
            config_dict = dict(overrides)
        else:
            config_dict = {}

        if self.system_instruction and "system_instruction" not in config_dict:
            config_dict["system_instruction"] = self.system_instruction

        if is_modern_gemini_model(self.model_name):
            for key in ("temperature", "top_p", "top_k", "candidate_count"):
                config_dict.pop(key, None)
            if self.thinking_level and "thinking_config" not in config_dict:
                config_dict["thinking_config"] = types.ThinkingConfig(
                    thinking_level=self.thinking_level
                )
        else:
            if (
                "temperature" not in config_dict
                and self.default_config.get("temperature") is not None
            ):
                config_dict["temperature"] = self.default_config["temperature"]

        return types.GenerateContentConfig(**config_dict)

    def configure(self, api_key: str):
        try:
            self.client = genai.Client(api_key=api_key)
            logger.info(f"Initialized Google GenAI Client: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to configure Google GenAI: {e}")
            raise

    def start_chat(self, history: List[Dict[str, Any]] = None) -> ChatSession:
        """
        Creates and returns a wrapper for the async chat session.
        """
        if not self.client:
            raise RuntimeError("Client not configured. Call configure() first.")

        # Convert history to Google Content types
        formatted_history = []
        if history:
            for item in history:
                formatted_history.append(
                    types.Content(
                        role=item["role"],
                        parts=[types.Part.from_text(text=p) for p in item["parts"]],
                    )
                )

        raw_chat = self.client.aio.chats.create(
            model=self.model_name,
            history=formatted_history,
            config=self._build_generate_config(),
        )
        return GoogleChatSession(raw_chat)

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

        raw_config = config if config is not None else legacy_config
        final_config = self._build_generate_config(raw_config)

        response = await self.client.aio.models.generate_content(
            model=self.model_name, contents=prompt, config=final_config, **kwargs
        )
        return response.text

    async def send_message_async(
        self, session: ChatSession, message: str, stream: bool = False
    ) -> AsyncGenerator[Any, None]:
        if not session:
            raise ValueError("Session cannot be None.")

        if isinstance(session, GoogleChatSession):
            raw_session = session._session
        else:
            # Fallback or error
            raw_session = session

        # session is now an AsyncChat object from client.aio.chats.create()
        if stream:
            # send_message_stream for async chat returns an awaitable async iterator
            response_stream = await raw_session.send_message_stream(message)
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
                if chunk.usage_metadata:
                    yield {"usage_metadata": chunk.usage_metadata}
        else:
            response = await raw_session.send_message(message)
            yield response.text
            if response.usage_metadata:
                yield {"usage_metadata": response.usage_metadata}
