import os
import re
import time
from typing import Optional

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("IngestScript")

EMBEDDING_BATCH_SIZE = 90
EMBEDDING_BATCH_DELAY_SECONDS = 62
MAX_BATCH_RETRIES = 3


def _extract_retry_delay(error_msg: str, default: float = 65.0) -> float:
    """Parses the suggested retry delay in seconds from a 429 error message."""
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", error_msg, re.IGNORECASE)
    if match:
        return max(float(match.group(1)) + 2.0, 5.0)
    return default


def _embed_batch_with_retry(
    vector_store: Optional[FAISS],
    batch: list,
    embeddings: GoogleGenerativeAIEmbeddings,
    batch_idx: int,
    total_batches: int,
) -> FAISS:
    """Embeds a single chunk batch into FAISS, retrying on Free Tier 429 errors."""
    for attempt in range(MAX_BATCH_RETRIES):
        try:
            if vector_store is None:
                return FAISS.from_documents(documents=batch, embedding=embeddings)
            vector_store.add_documents(batch)
            return vector_store
        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str
            if is_rate_limit and attempt < MAX_BATCH_RETRIES - 1:
                delay = _extract_retry_delay(err_str)
                logger.warning(
                    f"Rate limit on batch {batch_idx}/{total_batches} "
                    f"(attempt {attempt + 1}/{MAX_BATCH_RETRIES}). "
                    f"Sleeping {delay:.1f}s..."
                )
                time.sleep(delay)
                continue
            raise
    raise RuntimeError(f"Failed to embed batch {batch_idx}/{total_batches}.")


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

    # 4. Create Vector Store (FAISS) in rate-limited batches
    logger.info("Generating embeddings and creating FAISS Vector Store...")
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model=config.EMBEDDING_MODEL,
            google_api_key=config.GOOGLE_API_KEY.get_secret_value(),
        )

        batches = [
            chunks[i : i + EMBEDDING_BATCH_SIZE]
            for i in range(0, len(chunks), EMBEDDING_BATCH_SIZE)
        ]
        vector_store: Optional[FAISS] = None

        for batch_idx, batch in enumerate(batches, start=1):
            logger.info(
                f"Embedding batch {batch_idx}/{len(batches)} ({len(batch)} chunks)..."
            )
            vector_store = _embed_batch_with_retry(
                vector_store, batch, embeddings, batch_idx, len(batches)
            )
            if batch_idx < len(batches):
                logger.info(
                    f"Cooling down {EMBEDDING_BATCH_DELAY_SECONDS}s "
                    "for Free Tier RPM quota..."
                )
                time.sleep(EMBEDDING_BATCH_DELAY_SECONDS)

        if vector_store is None:
            logger.error("No chunks were embedded into the Vector Store.")
            return False

        # Save locally
        vector_store.save_local(persist_dir)

        logger.info(f"Success! Knowledge Base saved to {persist_dir}")
        return True

    except Exception as e:
        logger.error(f"Error creating Vector Store: {e}")
        return False


if __name__ == "__main__":
    run_ingestion()
