import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger("SemanticValidator")


class SemanticValidator:
    """
    Implements the Semantic Validation Module (SIC Patterns).
    Provides deterministic guardrails for Inputs and Router Outputs.
    """

    # Mock Regex patterns for sensitive data (PII)
    FORBIDDEN_PATTERNS = {
        "fake_api_key": r"sk-[a-zA-Z0-9]{20,}",
        "fake_credit_card": r"\b(?:\d[ -]*?){13,16}\b",
    }

    # Keywords that suggest jailbreak attempts or unsafe content
    FORBIDDEN_KEYWORDS = [
        "ignore all previous instructions",
        "jailbreak",
        "system override",
        "unrestricted mode",
    ]

    def validate(self, analysis_result: Dict[str, Any]) -> bool:
        """
        Validates the structure and safety of the Cognitive Router's output.
        """
        logger.info("Activating Semantic Validation Module...")

        # 1. Structural Integrity Check
        required_keys = ["natureza", "complexidade", "prioridade"]
        if not all(key in analysis_result for key in required_keys):
            logger.warning(
                f"❌ Structural Validation Failed. Missing keys: {required_keys}"
            )
            return False

        # 2. Safety Check (in synthesized intent if present)
        intent = analysis_result.get("intencao_sintetizada", "")
        if intent:
            if not self._validate_content_safety(intent):
                logger.warning("❌ Safety Validation Failed on Intent.")
                return False

        logger.info("✅ Semantic Validation Passed.")
        return True

    def validate_user_input(self, user_input: str) -> bool:
        """
        Public method to validate raw user input before processing.
        """
        return self._validate_content_safety(user_input)

    def _validate_content_safety(self, text: str) -> bool:
        """
        Internal check for PII patterns and forbidden keywords.
        """
        text_lower = text.lower()

        # Check Keywords
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in text_lower:
                logger.warning(f"Safety Trigger: Forbidden keyword found '{keyword}'")
                return False

        # Check Regex Patterns
        for name, pattern in self.FORBIDDEN_PATTERNS.items():
            if re.search(pattern, text):
                logger.warning(f"Safety Trigger: Sensitive pattern found ({name})")
                return False

        return True
