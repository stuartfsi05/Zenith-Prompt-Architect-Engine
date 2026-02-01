import os

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("IngestScript")


def run_ingestion() -> bool:
    """
    Runs the ingestion process: Loads docs, splits text, creates FAISS vector store.
    Returns True if successful, False otherwise.
    """
    config = Config()

    # 1. Configuration
    knowledge_dir = os.path.join(os.getcwd(), "knowledge_base")
    # FAISS uses a folder to store index.faiss and index.pkl
    persist_dir = os.path.join(os.getcwd(), "data", "vector_store")
    bm25_cache = os.path.join(os.getcwd(), "data", "bm25_index.pkl")

    # Cache Invalidation
    if os.path.exists(bm25_cache):
        try:
            os.remove(bm25_cache)
            logger.info("🗑️ BM25 Cache invalidated.")
        except Exception as e:
            logger.warning(f"Failed to delete BM25 cache: {e}")

    if not os.path.exists(knowledge_dir):
        logger.error(f"Directory not found: {knowledge_dir}")
        return False

    # 2. Load Documents
    logger.info("Scanning for .md and .txt files...")
    documents = []
    for root, _, files in os.walk(knowledge_dir):
        for file in files:
            if file.endswith(".md") or file.endswith(".txt"):
                file_path = os.path.join(root, file)
                try:
                    loader = TextLoader(file_path, encoding="utf-8")
                    docs = loader.load()
                    documents.extend(docs)
                    logger.info(f"Loaded: {file}")
                except Exception as e:
                    logger.error(f"Failed to load {file}: {e}")

    if not documents:
        logger.warning("No documents found to ingest.")
        return False

    # 3. Split Text
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, separators=["\n## ", "\n# ", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    logger.info(f"Created {len(chunks)} text chunks.")

    # 4. Create Vector Store (FAISS)
    logger.info("Generating embeddings and creating FAISS Vector Store...")
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", google_api_key=config.GOOGLE_API_KEY.get_secret_value()
        )

        # Initialize FAISS from documents
        vector_store = FAISS.from_documents(documents=chunks, embedding=embeddings)

        # Save locally
        vector_store.save_local(persist_dir)

        logger.info(f"Success! Knowledge Base saved to {persist_dir}")
        return True

    except Exception as e:
        logger.error(f"Error creating Vector Store: {e}")
        return False


if __name__ == "__main__":
    run_ingestion()
