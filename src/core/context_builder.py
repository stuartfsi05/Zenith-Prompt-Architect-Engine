import asyncio
import logging

logger = logging.getLogger("ContextBuilder")


class ContextBuilder:
    """
    Responsible for assembling the final prompt context, handling system injections,
    personas, and integrating RAG/Memory contexts.
    """

    def build_system_injection(self, persona: str) -> str:
        """
        Builds the system instruction string with the active persona.
        Native thinking is handled by the Gemini model's thinking_config.
        """
        return f"--- [SYSTEM OVERRIDE: ACTIVE PERSONA] ---\n{persona}\n"

    def format_rag_context(self, content: str) -> str:
        """Formats retrieved RAG content for prompt assembly."""
        if not content or not content.strip():
            return ""
        return f"--- [RELEVANT CONTEXT (Hybrid Search)] ---\n{content}\n\n"

    async def resolve_rag_context(
        self, knowledge_task: asyncio.Task, complexity: str
    ) -> str:
        """
        Resolves a pending knowledge retrieval task based on complexity.
        """
        rag_context = ""
        if complexity != "Simples":
            try:
                content = await knowledge_task
                rag_context = self.format_rag_context(content)
            except Exception as e:
                logger.error(f"Knowledge Retrieval failed: {e}")
        else:
            try:
                await knowledge_task
            except Exception:
                pass
        return rag_context

    def assemble_prompt(
        self,
        system_injection: str,
        memory_context: str,
        rag_context: str,
        user_input: str,
    ) -> str:
        """
        Combines all context parts into the final prompt string (static-first order).
        """
        return (
            f"{system_injection}\n"
            f"{memory_context}\n"
            f"{rag_context}\n"
            f"--- [USER REQUEST] ---\n{user_input}"
        )
