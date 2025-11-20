from pathlib import Path
from src.utils.logger import setup_logger

logger = setup_logger("ZenithLoader")

def load_system_prompt(filepath: str) -> str:
    """
    Securely loads the system prompt from the given filepath.
    Implements fallback logic to a sample prompt if the primary file is missing.

    Args:
        filepath (str): Path to the primary system prompt file.

    Returns:
        str: The content of the system prompt.

    Raises:
        FileNotFoundError: If neither the primary nor the sample file exists.
    """
    primary_path = Path(filepath)
    sample_path = Path("data/prompts/system_instruction.sample.md")

    if primary_path.exists():
        logger.info(f"Loading system prompt from: {primary_path}")
        try:
            return primary_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Error reading primary prompt file: {e}")
            # Proceed to fallback if read fails
            pass
    else:
        logger.warning(f"Primary system prompt not found at: {primary_path}")

    # Fallback Logic
    if sample_path.exists():
        logger.warning("⚠️  RUNNING IN DEMO MODE: Using sample system instruction. ⚠️")
        try:
            return sample_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.critical(f"Failed to read sample prompt file: {e}")
            raise FileNotFoundError(f"Could not read sample prompt at {sample_path}") from e
    else:
        logger.critical(f"System prompt file not found. Checked: {primary_path} and {sample_path}")
        raise FileNotFoundError("No system prompt file found. Please check configuration.")
