import os
import sys

# Force stdout to flush
sys.stdout.reconfigure(encoding="utf-8")

print("DEBUG: Starting ingestion...")

try:
    from langchain_community.document_loaders import TextLoader
    from langchain_community.vectorstores import FAISS
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    from src.core.config import Config

    print("DEBUG: Imports successful.")
except Exception as e:
    print(f"DEBUG: Import failed: {e}")
    sys.exit(1)


def run_ingestion() -> bool:
    print("DEBUG: Loading Config...")
    try:
        config = Config.load()
        print("DEBUG: Config loaded.")
    except Exception as e:
        print(f"DEBUG: Config load failed: {e}")
        return False

    knowledge_dir = os.path.join(os.getcwd(), "knowledge_base")
    persist_dir = os.path.join(os.getcwd(), "data", "vector_store")
    print(f"DEBUG: Knowledge Dir: {knowledge_dir}")
    print(f"DEBUG: Persist Dir: {persist_dir}")

    if not os.path.exists(knowledge_dir):
        print("DEBUG: Knowledge dir not found")
        return False

    # Ensure persist dir parent exists
    os.makedirs(os.path.dirname(persist_dir), exist_ok=True)

    print("DEBUG: Scanning files...")
    documents = []
    for root, _, files in os.walk(knowledge_dir):
        for file in files:
            if file.endswith(".md") or file.endswith(".txt"):
                file_path = os.path.join(root, file)
                try:
                    loader = TextLoader(file_path, encoding="utf-8")
                    docs = loader.load()
                    documents.extend(docs)
                    print(f"DEBUG: Loaded {file}")
                except Exception as e:
                    print(f"DEBUG: Failed to load {file}: {e}")

    if not documents:
        print("DEBUG: No documents found.")
        return False

    print("DEBUG: Splitting text...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    print(f"DEBUG: {len(chunks)} chunks created.")

    print("DEBUG: Generating Embeddings...")
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", google_api_key=config.GOOGLE_API_KEY
        )
        print("DEBUG: Embeddings initialized.")

        print("DEBUG: Creating FAISS index...")
        vector_store = FAISS.from_documents(documents=chunks, embedding=embeddings)
        print("DEBUG: FAISS index created.")

        print(f"DEBUG: Saving to {persist_dir}...")
        vector_store.save_local(persist_dir)
        print("DEBUG: Saved.")
        return True

    except Exception as e:
        print(f"DEBUG: Vector store creation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    if run_ingestion():
        print("DEBUG: SUCCESS")
    else:
        print("DEBUG: FAILURE")
