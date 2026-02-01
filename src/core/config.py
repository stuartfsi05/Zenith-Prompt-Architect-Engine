
import logging
from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils.logger import setup_logger

logger = setup_logger("ZenithConfig")

class Config(BaseSettings):
    """
    Configuration using Pydantic Settings for validation and fail-fast behavior.
    """
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        frozen=True
    )

    # Core
    GOOGLE_API_KEY: SecretStr
    MODEL_NAME: str = "gemini-2.5-flash"
    TEMPERATURE: float = Field(default=0.1, ge=0.0, le=1.0)
    
    # Paths (Dynamically computed defaults)
    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    
    @property
    def DATA_DIR(self) -> Path:
        return self.BASE_DIR / "data"

    @property
    def KNOWLEDGE_DIR(self) -> Path:
        return self.BASE_DIR / "knowledge_base"

    @property
    def VECTOR_STORE_DIR(self) -> Path:
        return self.DATA_DIR / "vector_store"

    @property
    def BM25_CACHE_PATH(self) -> Path:
        return self.DATA_DIR / "bm25_index.pkl"

    @property
    def SYSTEM_PROMPT_PATH(self) -> Path:
        return self.DATA_DIR / "prompts" / "system_instruction.md"

    @property
    def SAMPLE_SYSTEM_PROMPT_PATH(self) -> Path:
        return self.DATA_DIR / "prompts" / "system_instruction.sample.md"

    # Supabase (Optional but typed)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[SecretStr] = None

    def validate_secrets(self):
        """Optional explicit validation hook"""
        if not self.GOOGLE_API_KEY:
             raise ValueError("GOOGLE_API_KEY is missing!")
        if self.SUPABASE_URL and not self.SUPABASE_KEY:
             logger.warning("Supabase URL provided but Key is missing.")
