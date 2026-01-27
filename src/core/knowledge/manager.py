from typing import List

from langchain_core.documents import Document

from src.core.config import Config
from src.core.knowledge.reranker import RerankerService
from src.core.knowledge.retriever import HybridRetriever
from src.utils.logger import setup_logger

logger = setup_logger("KnowledgeManager")


class StrategicKnowledgeBase:
    """
    Facade for the Knowledge Retrieval System.
    Orchestrates Retriever and Reranker.
    """

    def __init__(self, config: Config):
        self.config = config
        self.retriever = HybridRetriever(config)
        self.reranker = RerankerService(config)
        self.is_initialized = False

    async def ensure_initialized(self):
        """Lazy async initialization."""
        if not self.is_initialized:
            await self.retriever.initialize()
            self.is_initialized = True

    async def retrieve_async(self, query: str, final_k: int = 3) -> str:
        """
        Main entry point for retrieval.
        """
        await self.ensure_initialized()
        
        # 1. Hybrid Retrieval (Vector + BM25)
        candidates = await self.retriever.retrieve(query)
        
        # 2. Limit candidates for Reranking (Cost/Speed optimization)
        top_candidates = candidates[:10]

        # 3. LLM Reranking
        final_docs = await self.reranker.rerank(query, top_candidates, top_n=final_k)

        return self._format_results(final_docs)

    def _format_results(self, docs: List[Document]) -> str:
        """Formats docs for context injection."""
        context_parts = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "Unknown")
            context_parts.append(
                f"[Documento {i+1} | Fonte: {source}]\n{doc.page_content}\n"
            )
        return "\n".join(context_parts)
