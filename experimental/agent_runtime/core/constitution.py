"""Constitution — AI Behavior Rules & Values

Implementation of CONSTITUTION.md.

The Constitution module defines behavioral constraints that go beyond
risk classification. While risk catches dangerous ACTIONS, constitution
catches dangerous BEHAVIOR and ethical violations.

Examples:
- Risk: "Don't send 10,000 emails" (rate limit)
- Constitution: "Never impersonate a human" (identity deception)

SOURCE OF TRUTH: ledger/core/CONSTITUTION.md
If this code contradicts the MD file, the MD file is correct.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json


class ConstitutionViolation(Exception):
    """Raised when an action violates the constitution."""
    pass


class RuleType(Enum):
    """Types of constitutional rules."""
    IDENTITY = "identity"           # Who the AI is/isn't
    DISCLOSURE = "disclosure"       # What must be revealed
    CONTENT = "content"             # What can/cannot be generated
    PRIVACY = "privacy"             # Data handling rules
    BIAS = "bias"                   # Fairness constraints
    SAFETY = "safety"               # Harm prevention
    CUSTOM = "custom"               # User-defined rules


@dataclass
class ConstitutionalRule:
    """A single constitutional rule."""
    
    text: str
    rule_type: RuleType
    enforced: bool = True
    severity: str = "high"  # high, medium, low
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def hash(self) -> str:
        """Hash of this rule for versioning."""
        content = f"{self.text}:{self.rule_type.value}:{self.severity}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass  
class Constitution:
    """A set of behavioral rules for AI agents.
    
    Similar to Anthropic's Constitutional AI or OpenAI's usage policies,
    but enforced at runtime through the governance layer.
    """
    
    rules: List[ConstitutionalRule] = field(default_factory=list)
    version: str = "1.0.0"
    
    def __init__(
        self,
        rules: Optional[List[str]] = None,
        version: str = "1.0.0"
    ):
        self.version = version
        self.rules = []
        
        if rules:
            for rule_text in rules:
                self.add_rule(rule_text)
    
    def add_rule(
        self,
        text: str,
        rule_type: RuleType = RuleType.CUSTOM,
        severity: str = "high"
    ) -> "Constitution":
        """Add a rule to the constitution."""
        self.rules.append(ConstitutionalRule(
            text=text,
            rule_type=rule_type,
            severity=severity
        ))
        return self
    
    def check(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> List[ConstitutionalRule]:
        """Check if an action violates any constitutional rules.
        
        Returns list of violated rules (empty if clean).
        """
        violated = []
        
        for rule in self.rules:
            if not rule.enforced:
                continue
                
            # Simple keyword-based checks (can be extended with LLM)
            if self._check_rule(rule, action, context):
                violated.append(rule)
        
        return violated
    
    def _check_rule(
        self,
        rule: ConstitutionalRule,
        action: str,
        context: Dict[str, Any]
    ) -> bool:
        """Check if a specific rule is violated.
        
        Returns True if VIOLATED (bad).
        """
        text_lower = rule.text.lower()
        
        # Identity rules
        if rule.rule_type == RuleType.IDENTITY:
            if "impersonate" in text_lower or "pretend to be" in text_lower:
                # Check if output claims to be human
                output = context.get("output", "")
                if self._claims_human_identity(output):
                    return True
        
        # Disclosure rules
        if rule.rule_type == RuleType.DISCLOSURE:
            if "disclose" in text_lower and "ai" in text_lower:
                # Check if AI identity is disclosed
                output = context.get("output", "")
                if not self._discloses_ai_identity(output):
                    return True
        
        # Content rules
        if rule.rule_type == RuleType.CONTENT:
            if "harmful" in text_lower or "illegal" in text_lower:
                output = context.get("output", "")
                if self._contains_harmful_content(output):
                    return True
        
        # Privacy rules
        if rule.rule_type == RuleType.PRIVACY:
            if "privacy" in text_lower or "confidential" in text_lower:
                # Check for PII leakage
                output = context.get("output", "")
                if self._contains_pii(output):
                    return True
        
        return False
    
    def _claims_human_identity(self, text: str) -> bool:
        """Check if text claims to be human."""
        indicators = [
            "i am a human",
            "i'm a human",
            "i am a person",
            "i'm a person",
            "i have feelings",
            "i am real"
        ]
        text_lower = text.lower()
        return any(ind in text_lower for ind in indicators)
    
    def _discloses_ai_identity(self, text: str) -> bool:
        """Check if text discloses AI identity."""
        indicators = [
            "i am an ai",
            "i'm an ai",
            "i am a language model",
            "i'm an assistant",
            "as an ai"
        ]
        text_lower = text.lower()
        return any(ind in text_lower for ind in indicators)
    
    def _contains_harmful_content(self, text: str) -> bool:
        """Check for harmful content (simplified)."""
        # This would integrate with content moderation API
        # For now, placeholder
        harmful_keywords = [
            "kill yourself",
            "how to make a bomb",
            "create malware"
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in harmful_keywords)
    
    def _contains_pii(self, text: str) -> bool:
        """Check for PII leakage (simplified)."""
        # This would use regex for SSN, credit cards, etc.
        # For now, placeholder
        return False
    
    @property
    def hash(self) -> str:
        """Hash of entire constitution for versioning."""
        rule_hashes = [r.hash for r in self.rules]
        content = f"{self.version}:{':'.join(rule_hashes)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "version": self.version,
            "hash": self.hash,
            "rules": [
                {
                    "text": r.text,
                    "type": r.rule_type.value,
                    "severity": r.severity,
                    "hash": r.hash
                }
                for r in self.rules
            ]
        }


# Pre-defined constitutions for common use cases

SAFETY_CONSTITUTION = Constitution([
    "Never generate content that promotes self-harm",
    "Never generate content that promotes violence",
    "Never generate instructions for creating weapons",
    "Never generate sexually explicit content involving minors",
])

TRANSPARENCY_CONSTITUTION = Constitution([
    "Always disclose when you are an AI",
    "Never impersonate a human",
    "Always acknowledge the limitations of your knowledge",
])

PRIVACY_CONSTITUTION = Constitution([
    "Never share user data with third parties",
    "Always protect confidential information",
    "Never retain personal data longer than necessary",
])

# Combined default constitution
DEFAULT_CONSTITUTION = Constitution([
    "Never impersonate a human",
    "Always disclose when acting as AI",
    "Never generate harmful or illegal content",
    "Respect user privacy and confidentiality",
    "Avoid biased or discriminatory outputs",
])
