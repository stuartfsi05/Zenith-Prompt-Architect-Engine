import asyncio
import glob
import os
from typing import List, Dict

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from rank_bm25 import BM25Okapi

from src.core.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("Retriever")


class HybridRetriever:
    """
    Handles retrieval from Vector Store (FAISS) and Keyword Search (BM25).
    """

    def __init__(self, config: Config):
        self.config = config
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=self.config.GOOGLE_API_KEY
        )
        self.vector_store = None
        self.bm25_index = None
        self.bm25_corpus = []

    async def initialize(self):
        """
        Async initialization of stores.
        """
        loop = asyncio.get_running_loop()
        
        # Load Vector DB
        await loop.run_in_executor(None, self._load_vector_db)
        
        # Build BM25 Index (Rebuild in memory to avoid pickle risks)
        await loop.run_in_executor(None, self._build_bm25_index)

    def _load_vector_db(self):
        """Loads FAISS vector store."""
        if os.path.exists(os.path.join(self.config.VECTOR_STORE_DIR, "index.faiss")):
            try:
                self.vector_store = FAISS.load_local(
                    folder_path=self.config.VECTOR_STORE_DIR,
                    embeddings=self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info("FAISS Vector DB loaded.")
            except Exception as e:
                logger.error(f"Failed to load Vector DB: {e}")
        else:
            logger.warning("No Vector DB found.")

    def _build_bm25_index(self):
        """Builds in-memory BM25 index from source files."""
        try:
            files = glob.glob(os.path.join(self.config.KNOWLEDGE_DIR, "*.md"))
            documents = []

            for fpath in files:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                    chunks = [p for p in content.split("\n\n") if len(p) > 50]
                    for chunk in chunks:
                        documents.append({
                            "content": chunk,
                            "source": os.path.basename(fpath)
                        })

            if documents:
                tokenized_corpus = [doc["content"].split() for doc in documents]
                self.bm25_index = BM25Okapi(tokenized_corpus)
                self.bm25_corpus = documents
                logger.info(f"BM25 Index built ({len(documents)} chunks).")
            else:
                logger.warning("No documents found for BM25.")

        except Exception as e:
            logger.error(f"Failed to build BM25 Index: {e}")

    async def retrieve(self, query: str) -> List[Document]:
        """
        Executes parallel search and returns combined results.
        """
        loop = asyncio.get_running_loop()
        
        vector_task = loop.run_in_executor(None, lambda: self._vector_search(query))
        bm25_task = loop.run_in_executor(None, lambda: self._bm25_search(query))

        vector_docs, bm25_docs = await asyncio.gather(vector_task, bm25_task)
        
        return self._reciprocal_rank_fusion(vector_docs, bm25_docs)

    def _vector_search(self, query: str) -> List[Document]:
        if not self.vector_store:
            return []
        try:
            return self.vector_store.similarity_search(query, k=10)
        except Exception as e:
            logger.warning(f"Vector search failed: {e}")
            return []

    def _bm25_search(self, query: str) -> List[Document]:
        if not self.bm25_index:
            return []
        
        tokenized_query = query.split()
        results = self.bm25_index.get_top_n(tokenized_query, self.bm25_corpus, n=10)
        
        return [
            Document(page_content=d["content"], metadata={"source": d["source"]})
            for d in results
        ]

    def _reciprocal_rank_fusion(
        self, list_a: List[Document], list_b: List[Document], k=60
    ) -> List[Document]:
        scores = {}

        def get_doc_id(doc):
            return hash(doc.page_content)

        for rank, doc in enumerate(list_a):
            doc_id = get_doc_id(doc)
            if doc_id not in scores:
                scores[doc_id] = {"doc": doc, "score": 0}
            scores[doc_id]["score"] += 1 / (k + rank)

        for rank, doc in enumerate(list_b):
            doc_id = get_doc_id(doc)
            if doc_id not in scores:
                scores[doc_id] = {"doc": doc, "score": 0}
            scores[doc_id]["score"] += 1 / (k + rank)

        sorted_docs = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
        return [item["doc"] for item in sorted_docs]
