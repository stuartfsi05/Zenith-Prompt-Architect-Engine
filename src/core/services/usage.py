import logging
from typing import Any, Dict

from src.core.database import PersistenceLayer

logger = logging.getLogger("UsageService")


class UsageService:
    """
    Service responsible for tracking and logging token usage.
    """

    def __init__(self, db: PersistenceLayer):
        self.db = db

    def log_tokens(
        self,
        user_id: str,
        session_id: str,
        model_name: str,
        usage_metadata: Dict[str, Any],
    ) -> None:
        """
        Parses usage metadata and logs it to persistence layer.
        """
        if not usage_metadata:
            return

        try:
            # Handle google.genai.types.UsageMetadata object or dict
            if hasattr(usage_metadata, "prompt_token_count"):
                input_tokens = usage_metadata.prompt_token_count or 0
                output_tokens = usage_metadata.candidates_token_count or 0
                total_tokens = usage_metadata.total_token_count or 0
            elif isinstance(usage_metadata, dict):
                input_tokens = usage_metadata.get("prompt_token_count") or 0
                output_tokens = usage_metadata.get("candidates_token_count") or 0
                total_tokens = usage_metadata.get("total_token_count") or 0
            else:
                logger.warning(f"Unknown usage metadata format: {type(usage_metadata)}")
                return

            if total_tokens == 0:
                return

            self.db.log_usage(
                user_id=user_id,
                session_id=session_id,
                model=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            )
            logger.debug(f"Logged {total_tokens} tokens for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to log tokens: {e}")
