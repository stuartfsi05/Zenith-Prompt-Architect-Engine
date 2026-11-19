from typing import List, Optional

from src.core.config import Config
from src.core.knowledge.retriever import Document
from src.core.llm.google_genai import GoogleGenAIProvider
from src.utils.json_utils import parse_llm_json
from src.utils.logger import setup_logger

logger = setup_logger("Reranker")


class RerankerService:
    """
    Uses LLM to re-rank documents based on relevance to the query.
    """

    def __init__(self, config: Config, api_key: Optional[str] = None):
        self.config = config
        effective_key = api_key or self.config.GOOGLE_API_KEY.get_secret_value()
        self.llm = GoogleGenAIProvider(
            model_name=self.config.AUX_MODEL_NAME,
            temperature=0.0,
            thinking_level=self.config.AUX_THINKING_LEVEL,
        )
        self.llm.configure(effective_key)

    async def rerank(
        self, query: str, candidates: List[Document], top_n: int = 3
    ) -> List[Document]:
        """
        Re-ranks the candidate documents using the LLM.
        """
        if not candidates:
            return []

        logger.info("Performing LLM Reranking logic...")

        candidates_text = ""
        for i, doc in enumerate(candidates):
            candidates_text += f"[ID: {i}] Content: {doc.page_content[:300]}...\n\n"

        prompt = f"""
        TAREFA: Cross-Encoder Reranking
        QUERY: "{query}"

        DOCUMENTOS CANDIDATOS:
        {candidates_text}

        SELECIONE OS {top_n} documentos MAIS RELEVANTES para responder à query.
        Retorne APENAS um JSON com a lista de IDs em ordem de relevância.
        Exemplo: [0, 4, 1]
        """

        try:
            response_text = await self.llm.generate_content_async(
                prompt, config={"response_mime_type": "application/json"}
            )

            selected_ids = parse_llm_json(response_text)
            if not isinstance(selected_ids, list):
                return candidates[:top_n]

            reranked_docs = []
            for idx in selected_ids:
                if isinstance(idx, int) and 0 <= idx < len(candidates):
                    reranked_docs.append(candidates[idx])

            return reranked_docs if reranked_docs else candidates[:top_n]

        except Exception as e:
            logger.warning(f"Reranking failed ({e}). Returning original order.")
            return candidates[:top_n]
