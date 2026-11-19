from pathlib import Path
from typing import Literal, Optional

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
        frozen=True,
        str_strip_whitespace=True,
    )

    # Core
    GOOGLE_API_KEY: SecretStr
    MODEL_NAME: str = "gemini-3.8-flash"
    AUX_MODEL_NAME: str = "gemini-3.5-flash-lite"
    EMBEDDING_MODEL: str = "models/gemini-embedding-2"
    THINKING_LEVEL: Literal["low", "medium", "high"] = "medium"
    AUX_THINKING_LEVEL: Literal["minimal", "low", "medium", "high"] = "minimal"
    TEMPERATURE: float = Field(default=0.1, ge=0.0, le=1.0)
    DEMO_DAILY_LIMIT: int = Field(default=5, ge=1, le=100)
    ALLOWED_ORIGINS: str = (
        "http://localhost:5173,http://localhost:3000,https://zenith-interface.vercel.app"
    )
    SYSTEM_PROMPT_OVERRIDE: Optional[str] = Field(
        default=None, alias="SYSTEM_PROMPT_PATH"
    )

    # Paths (Dynamically computed defaults)
    BASE_DIR: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent
    )

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parses comma-separated CORS origins into a clean list."""
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

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
        if self.SYSTEM_PROMPT_OVERRIDE:
            candidate = Path(self.SYSTEM_PROMPT_OVERRIDE)
            if not candidate.is_absolute():
                candidate = self.BASE_DIR / candidate
            if candidate.exists():
                return candidate
        default_md = self.DATA_DIR / "prompts" / "system_instruction.md"
        if default_md.exists():
            return default_md
        return self.SAMPLE_SYSTEM_PROMPT_PATH

    @property
    def SAMPLE_SYSTEM_PROMPT_PATH(self) -> Path:
        return self.DATA_DIR / "prompts" / "system_instruction.sample.md"

    # Supabase (Optional but typed)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[SecretStr] = None

    # E-mail (Feedback)
    SMTP_SERVER: Optional[str] = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[SecretStr] = None

    def validate_secrets(self):
        """Optional explicit validation hook"""
        if not self.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is missing!")
        if self.SUPABASE_URL and not self.SUPABASE_KEY:
            logger.warning("Supabase URL provided but Key is missing.")
