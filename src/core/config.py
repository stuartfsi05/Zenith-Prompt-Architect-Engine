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

    @classmethod
    def load(cls) -> "Config":
        """
        Loads environment variables and validates critical configurations.
        """
        load_dotenv()

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.critical(
                "GOOGLE_API_KEY not found in environment variables."
            )
            raise ValueError(
                "GOOGLE_API_KEY is required. Please check your .env file."
            )

        model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")

        try:
            temperature = float(os.getenv("TEMPERATURE", "0.1"))
        except ValueError:
            logger.warning(
                "Invalid TEMPERATURE value in .env. Defaulting to 0.1."
            )
            temperature = 0.1

        system_prompt_path = os.getenv(
            "SYSTEM_PROMPT_PATH",
            "data/prompts/system_instruction.sample.md"
        )

        return cls(
            GOOGLE_API_KEY=api_key,
            MODEL_NAME=model_name,
            TEMPERATURE=temperature,
            SYSTEM_PROMPT_PATH=system_prompt_path,
        )
