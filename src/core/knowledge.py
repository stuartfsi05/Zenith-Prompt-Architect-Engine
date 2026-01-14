import os
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from src.core.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("KnowledgeBase")


class StrategicKnowledgeBase:
    """
    Manages the Retrieval-Augmented Generation (RAG) system.
    Uses ChromaDB to store and retrieve document chunks.
    """

    def __init__(self, config: Config):
        self.config = config
        self.persist_directory = os.path.join(os.getcwd(), "data", "chroma_db")
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", google_api_key=self.config.GOOGLE_API_KEY
        )
        self.vector_store = None
        self._load_db()

    def _load_db(self):
        """Loads the existing vector store if it exists."""
        if os.path.exists(self.persist_directory):
            try:
                self.vector_store = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings,
                )
                logger.info(f"Knowledge Base loaded from {self.persist_directory}")
            except Exception as e:
                logger.error(f"Failed to load Knowledge Base: {e}")
        else:
            logger.warning(
                f"No existing Knowledge Base found at {self.persist_directory}. Please run ingestion script."
            )

    def retrieve(self, query: str, k: int = 3) -> str:
        """
        Retrieves relevant context for a given query.
        Returns a formatted string of the top-k documents.
        """
        if not self.vector_store:
            return ""

        try:
            logger.info(f"Querying Knowledge Base for: '{query}'")
            results = self.vector_store.similarity_search(query, k=k)

            if not results:
                logger.info("No relevant documents found.")
                return ""

            context_parts = []
            for i, doc in enumerate(results):
                source = doc.metadata.get("source", "Unknown")
                content = doc.page_content
                context_parts.append(
                    f"[Documento {i+1} | Fonte: {source}]\n{content}\n"
                )

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return ""
