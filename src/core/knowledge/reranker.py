from src.core.config import Config
from src.core.llm.google_genai import GoogleGenAIProvider
from src.utils.logger import setup_logger

logger = setup_logger("Reranker")


class RerankerService:
    """
    Uses LLM to re-rank documents based on relevance to the query.
    """

    def __init__(self, config: Config):
        self.config = config
        # Ideally injected, but for now we instantiate here to minimize breaking changes
        self.llm = GoogleGenAIProvider(
            model_name=self.config.MODEL_NAME, 
            temperature=0.0
        )
        self.llm.configure(self.config.GOOGLE_API_KEY)

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
            # Using LLM Provider Abstraction
            response_text = await self.llm.generate_content_async(
                prompt,
                response_mime_type="application/json"
            )

            selected_ids = json.loads(response_text)
            reranked_docs = []
            
            # Defensive coding against hallucinated IDs
            for idx in selected_ids:
                if isinstance(idx, int) and 0 <= idx < len(candidates):
                    reranked_docs.append(candidates[idx])

            return reranked_docs if reranked_docs else candidates[:top_n]

        except Exception as e:
            logger.warning(f"Reranking failed ({e}). Returning original order.")
            return candidates[:top_n]
