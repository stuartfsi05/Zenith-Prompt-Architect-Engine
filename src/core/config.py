import os
from dataclasses import dataclass

from dotenv import load_dotenv

from src.utils.logger import setup_logger

# Initialize logger for config module
logger = setup_logger("ZenithConfig")


@dataclass(frozen=True)
class Config:
    """
    Configuration dataclass to hold environment variables and settings.
    Implements Singleton pattern via module-level instance.
    """

    GOOGLE_API_KEY: str
    MODEL_NAME: str
    TEMPERATURE: float
    SYSTEM_PROMPT_PATH: str

    @classmethod
    def load(cls) -> "Config":
        """
        Loads environment variables and validates critical configurations.

        Returns:
            Config: An instance of the Config class.

        Raises:
            ValueError: If GOOGLE_API_KEY is missing.
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

        system_prompt_path = os.getenv(
            "SYSTEM_PROMPT_PATH", "data/prompts/system_instruction.sample.md"
        )

        # logger.info(f"Configuration loaded. Model: {model_name}")

        return cls(
            GOOGLE_API_KEY=api_key,
            MODEL_NAME=model_name,
            TEMPERATURE=temperature,
            SYSTEM_PROMPT_PATH=system_prompt_path,
        )


# Global config instance
try:
    # We don't auto-load here to allow for controlled loading in main
    # but for simple access we can provide a lazy loader or just let
    # main handle it.
    # For this architecture, we will let the main entry point or agent
    # trigger the load to ensure exception handling is done at the right level.
    pass
except Exception as e:
    logger.error(f"Failed to initialize configuration: {e}")
