import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger("ContextBuilder")

class ContextBuilder:
    """
    Responsible for assembling the final prompt context, handling system injections,
    personas, and integrating RAG/Memory contexts.
    """

    def build_system_injection(self, persona: str) -> str:
        """
        Builds the system instruction string with the active persona and mandatory thinking instructions.
        """
        return (
            f"--- [SYSTEM OVERRIDE: ACTIVE PERSONA] ---\n{persona}\n\n"
            f"--- [MANDATORY INSTRUCTION: DEEP THINKING] ---\n"
            f"Antes de responder, você DEVE analisar o pedido passo a passo "
            f"dentro de tags <thinking>...</thinking>.\n"
            f"Planeje sua resposta, verifique fatos e critique sua própria lógica.\n"
            f"Apenas após o fechamento da tag </thinking>, forneça a resposta final ao usuário.\n"
        )

    async def resolve_rag_context(self, knowledge_task: asyncio.Task, complexity: str) -> str:
        """
        Resolves the pending knowledge retrieval task and formats the context based on complexity.
        """
        rag_context = ""
        if complexity != "Simples":
            try:
                content = await knowledge_task
                if content:
                    rag_context = f"--- [RELEVANT CONTEXT (Hybrid Search)] ---\n{content}\n\n"
            except Exception as e:
                logger.error(f"Knowledge Retrieval failed: {e}")
        else:
            # We still await to ensure task cleanup, but ignore result
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
        user_input: str
    ) -> str:
        """
        Combines all context parts into the final prompt string.
        """
        return f"{system_injection}\n\n{memory_context}\n{rag_context}\n--- [USER REQUEST] ---\n{user_input}"
