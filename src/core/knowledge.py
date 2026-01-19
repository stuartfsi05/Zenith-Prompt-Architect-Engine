import os
import glob
import logging
import pickle
from typing import List, Tuple
from rank_bm25 import BM25Okapi
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain_core.documents import Document

from src.core.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("KnowledgeBase")


class StrategicKnowledgeBase:
    """
    SOTA Knowledge Retrieval Module.
    Implements Hybrid Search (Vector + BM25) with Reciprocal Rank Fusion & LLM Reranking.
    """

    def __init__(self, config: Config):
        self.config = config
        self.persist_directory = os.path.join(os.getcwd(), "data", "chroma_db")
        self.bm25_cache_path = os.path.join(os.getcwd(), "data", "bm25_index.pkl")
        self.knowledge_dir = os.path.join(os.getcwd(), "knowledge_base")
        
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", google_api_key=self.config.GOOGLE_API_KEY
        )
        
        # Initialize Retrievers
        self.vector_store = None
        self.bm25_index = None
        self.bm25_corpus = []  # Stores (content, metadata)
        
        self._load_vector_db()
        self._build_bm25_index()
        
        # Lightweight model for Reranking
        self.reranker_model = genai.GenerativeModel("gemini-3-flash-preview")

    def _load_vector_db(self):
        """Loads the existing Chroma vector store."""
        if os.path.exists(self.persist_directory):
            try:
                self.vector_store = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings,
                )
                logger.info(f"✅ Vector DB loaded from {self.persist_directory}")
            except Exception as e:
                logger.error(f"❌ Failed to load Vector DB: {e}")
        else:
            logger.warning(f"⚠️ No Vector DB found at {self.persist_directory}")

    def _build_bm25_index(self):
        """Builds in-memory BM25 index or loads from cache."""
        # 1. Try Loading from Cache
        if os.path.exists(self.bm25_cache_path):
            try:
                with open(self.bm25_cache_path, "rb") as f:
                    data = pickle.load(f)
                    self.bm25_index = data["index"]
                    self.bm25_corpus = data["corpus"]
                logger.info(f"✅ BM25 Index loaded from cache ({len(self.bm25_corpus)} chunks).")
                return
            except Exception as e:
                logger.warning(f"⚠️ Failed to load BM25 cache: {e}. Rebuilding...")

        # 2. Rebuild Index
        try:
            files = glob.glob(os.path.join(self.knowledge_dir, "*.md"))
            documents = []
            
            for fpath in files:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Naive chunking for BM25
                    chunks = [p for p in content.split("\n\n") if len(p) > 50]
                    for chunk in chunks:
                        documents.append({"content": chunk, "source": os.path.basename(fpath)})
            
            if documents:
                tokenized_corpus = [doc["content"].split() for doc in documents]
                self.bm25_index = BM25Okapi(tokenized_corpus)
                self.bm25_corpus = documents
                
                # 3. Save to Cache
                with open(self.bm25_cache_path, "wb") as f:
                    pickle.dump({"index": self.bm25_index, "corpus": self.bm25_corpus}, f)
                
                logger.info(f"✅ BM25 Index built and cached with {len(documents)} chunks.")
            else:
                logger.warning("⚠️ No documents found for BM25 indexing.")
                
        except Exception as e:
            logger.error(f"❌ Failed to build BM25 Index: {e}")

    def retrieve(self, query: str, final_k: int = 3) -> str:
        """
        Executes Hybrid Retrieval Pipeline:
        1. Vector Search (High Semantic Recall)
        2. BM25 Search (High Keyword Precision)
        3. Reciprocal Rank Fusion (RRF)
        4. LLM Agentic Reranking (Context Precision)
        """
        if not self.vector_store or not self.bm25_index:
            return ""

        logger.info(f"🔎 Executing Hybrid Search for: '{query}'")

        # 1. Vector Retrieval
        vector_docs = self.vector_store.similarity_search(query, k=10)
        
        # 2. BM25 Retrieval
        tokenized_query = query.split()
        bm25_docs = self.bm25_index.get_top_n(tokenized_query, self.bm25_corpus, n=10)
        
        # Normalize BM25 docs to LangChain Document format for fusion (mocking object)
        bm25_lc_docs = [
            Document(page_content=d["content"], metadata={"source": d["source"]}) 
            for d in bm25_docs
        ]

        # 3. Reciprocal Rank Fusion
        fused_results = self._reciprocal_rank_fusion(vector_docs, bm25_lc_docs, k=60)
        top_candidates = fused_results[:10]  # Take Top-10 for Re-ranking
        
        # 4. LLM Reranking
        final_docs = self._llm_reranking(query, top_candidates, top_n=final_k)
        
        return self._format_results(final_docs)

    def _reciprocal_rank_fusion(self, list_a: List[Document], list_b: List[Document], k=60) -> List[Document]:
        """
        Combines two ranked lists using RRF algorithm.
        Score = 1 / (k + rank)
        """
        scores = {}
        
        # Helper to hash document content for deduplication
        def get_doc_id(doc):
            return hash(doc.page_content)

        # Process List A (Vector)
        for rank, doc in enumerate(list_a):
            doc_id = get_doc_id(doc)
            if doc_id not in scores:
                scores[doc_id] = {"doc": doc, "score": 0}
            scores[doc_id]["score"] += 1 / (k + rank)

        # Process List B (BM25)
        for rank, doc in enumerate(list_b):
            doc_id = get_doc_id(doc)
            if doc_id not in scores:
                scores[doc_id] = {"doc": doc, "score": 0}
            scores[doc_id]["score"] += 1 / (k + rank)

        # Sort by score descending
        sorted_docs = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
        return [item["doc"] for item in sorted_docs]

    def _llm_reranking(self, query: str, candidates: List[Document], top_n: int = 3) -> List[Document]:
        """
        Uses Gemini to assess relevance of each candidate against the query.
        Returns the top_n most relevant documents.
        """
        logger.info("🧠 Performing LLM Reranking on Top-10 candidates...")
        
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
            response = self.reranker_model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json", "temperature": 0.0}
            )
            import json
            selected_ids = json.loads(response.text)
            
            # Filter and order documents
            reranked_docs = []
            for idx in selected_ids:
                if 0 <= idx < len(candidates):
                    reranked_docs.append(candidates[idx])
            
            logger.info(f"✅ Reranking selected IDs: {selected_ids}")
            return reranked_docs if reranked_docs else candidates[:top_n]

        except Exception as e:
            logger.warning(f"⚠️ Reranking failed ({e}). Returning Top-{top_n} from RRF.")
            return candidates[:top_n]

    def _format_results(self, docs: List[Document]) -> str:
        """Formats docs for context injection."""
        context_parts = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "Unknown")
            context_parts.append(f"[Documento {i+1} | Fonte: {source}]\n{doc.page_content}\n")
        return "\n".join(context_parts)
