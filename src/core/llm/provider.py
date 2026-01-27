from abc import ABC, abstractmethod
from typing import AsyncGenerator, Any, Dict, List, Optional

class LLMProvider(ABC):
    """
    Abstract Base Class for Language Model Providers.
    Ensures the system is agnostic to the underlying model API (Google, OpenAI, etc).
    """

    @abstractmethod
    def configure(self, api_key: str):
        """Configures the provider authentication."""
        pass

    @abstractmethod
    def start_chat(self, history: List[Dict[str, Any]] = None) -> Any:
        """Starts a chat session with history."""
        pass

    @abstractmethod
    async def generate_content_async(self, prompt: str, **kwargs) -> str:
        """Generates a single response asynchronously."""
        pass
    
    @abstractmethod
    async def send_message_async(self, session: Any, message: str, stream: bool = False) -> AsyncGenerator[str, None]:
        """Sends a message to an active session and returns stream/text."""
        pass
