import os
from dataclasses import dataclass

from dotenv import load_dotenv

from src.utils.logger import setup_logger

logger = setup_logger("ZenithConfig")


@dataclass(frozen=True)
class Config:
    """
    Configuration dataclass to hold environment variables and settings.
    """

    GOOGLE_API_KEY: str
    MODEL_NAME: str
    TEMPERATURE: float
    SYSTEM_PROMPT_PATH: str
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Paths
    DATA_DIR: str
    KNOWLEDGE_DIR: str
    VECTOR_STORE_DIR: str
    BM25_CACHE_PATH: str

    @classmethod
    def load(cls) -> "Config":
        """
        Loads environment variables and validates critical configurations.
        """
        load_dotenv()

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.critical("GOOGLE_API_KEY not found in environment variables.")
            raise ValueError("GOOGLE_API_KEY is required. Please check your .env file.")

        model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")

        try:
            temperature = float(os.getenv("TEMPERATURE", "0.1"))
        except ValueError:
            logger.warning("Invalid TEMPERATURE value in .env. Defaulting to 0.1.")
            temperature = 0.1

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
             logger.warning("SUPABASE_URL or SUPABASE_KEY not found. Database features may fail.")

        base_dir = os.getcwd()

        system_prompt_path = os.getenv(
            "SYSTEM_PROMPT_PATH",
            os.path.join(base_dir, "data", "prompts", "system_instruction.sample.md"),
        )

        data_dir = os.path.join(base_dir, "data")
        knowledge_dir = os.path.join(base_dir, "knowledge_base")
        vector_store_dir = os.path.join(data_dir, "vector_store")
        bm25_cache_path = os.path.join(data_dir, "bm25_index.pkl")

        return cls(
            GOOGLE_API_KEY=api_key,
            MODEL_NAME=model_name,
            TEMPERATURE=temperature,
            SYSTEM_PROMPT_PATH=system_prompt_path,
            SUPABASE_URL=supabase_url or "",
            SUPABASE_KEY=supabase_key or "",
            DATA_DIR=data_dir,
            KNOWLEDGE_DIR=knowledge_dir,
            VECTOR_STORE_DIR=vector_store_dir,
            BM25_CACHE_PATH=bm25_cache_path,
        )
