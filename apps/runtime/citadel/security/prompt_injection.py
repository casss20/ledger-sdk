"""Prompt injection detection for action payloads.

Detects common LLM prompt injection patterns in action payloads
before they reach policy evaluation or execution.
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:previous\s+)?instructions",
    r"system\s*[\:\-]\s*(?:you\s+are|ignore|override|disregard)",
    r"developer\s*[\:\-]\s*(?:you\s+are|ignore|override|disregard)",
    r"DAN\s*[\:\-]\s*(?:mode|prompt|enabled)",
    r"jailbreak\s*[\:\-]\s*(?:enabled|mode|prompt)",
    r"\bignore\s+above\s+constraints\b",
    r"\bdisregard\s+(?:the\s+)?(?:previous|above)\s+(?:instructions|rules|constraints)\b",
    r"\bnew\s+instruction[s]?\s*[\:\-]\s*",
    r"\boverride\s+(?:the\s+)?(?:previous|above)\s+(?:instructions|rules|constraints)\b",
]


class PromptInjectionDetector:
    """Detects prompt injection attempts in action payloads."""

    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS]

    def scan(self, payload: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Scan a payload dict for prompt injection patterns.

        Returns (is_clean, matched_patterns).
        """
        matched = []
        text = self._flatten_payload(payload)
        for pattern in self.patterns:
            if pattern.search(text):
                matched.append(pattern.pattern)
        return (not matched, matched)

    def _flatten_payload(self, payload: Dict[str, Any]) -> str:
        """Flatten nested dict to searchable string."""
        parts = []
        for key, value in payload.items():
            parts.append(str(key))
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, dict):
                parts.append(self._flatten_payload(value))
            elif isinstance(value, list):
                for item in value:
                    parts.append(str(item))
        return " ".join(parts)
