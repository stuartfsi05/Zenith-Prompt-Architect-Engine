import logging
import re
from typing import Any, Dict

logger = logging.getLogger("SemanticValidator")


def _luhn_check(digits: str) -> bool:
    """Validates whether a numeric string passes the Luhn credit card checksum."""
    if not digits.isdigit():
        return False
    total = 0
    reverse_digits = digits[::-1]
    for idx, ch in enumerate(reverse_digits):
        n = int(ch)
        if idx % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


class SemanticValidator:
    """
    Implements the Semantic Validation Module (SIC Patterns).
    Provides deterministic guardrails for Inputs and Router Outputs.
    """

    MAX_INPUT_LENGTH = 12000

    # Patterns for real secret credentials (API keys and tokens)
    FORBIDDEN_PATTERNS = {
        "openai_api_key": r"\bsk-[a-zA-Z0-9_-]{20,}\b",
        "google_api_key": r"\bAIza[0-9A-Za-z_-]{35}\b",
        "github_token": r"\bghp_[a-zA-Z0-9]{36}\b",
        "aws_access_key": r"\bAKIA[0-9A-Z]{16}\b",
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

        required_keys = ["natureza", "complexidade", "prioridade"]
        if not all(key in analysis_result for key in required_keys):
            logger.warning(
                f"Structural Validation Failed. Missing keys: {required_keys}"
            )
            return False

        intent = analysis_result.get("intencao_sintetizada", "")
        if intent and not self._validate_content_safety(intent):
            logger.warning("Safety Validation Failed on Intent.")
            return False

        logger.info("Semantic Validation Passed.")
        return True

    def validate_user_input(self, user_input: str) -> bool:
        """
        Public method to validate raw user input before processing.
        """
        if not user_input or not user_input.strip():
            return False
        if len(user_input) > self.MAX_INPUT_LENGTH:
            logger.warning(
                f"Safety Trigger: Input exceeds MAX_INPUT_LENGTH ({len(user_input)})."
            )
            return False
        return self._validate_content_safety(user_input)

    def _contains_credit_card(self, text: str) -> bool:
        """Checks 13-19 digit sequences using Luhn to avoid CNPJ/ID false positives."""
        for match in re.finditer(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)", text):
            digits = re.sub(r"\D", "", match.group(0))
            if 13 <= len(digits) <= 19 and _luhn_check(digits):
                return True
        return False

    def _validate_content_safety(self, text: str) -> bool:
        """
        Internal check for PII patterns, secret keys, and forbidden keywords.
        """
        text_lower = text.lower()

        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in text_lower:
                logger.warning(f"Safety Trigger: Forbidden keyword found '{keyword}'")
                return False

        for name, pattern in self.FORBIDDEN_PATTERNS.items():
            if re.search(pattern, text):
                logger.warning(f"Safety Trigger: Sensitive pattern found ({name})")
                return False

        if self._contains_credit_card(text):
            logger.warning("Safety Trigger: Sensitive pattern found (credit_card)")
            return False

        return True
