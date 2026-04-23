"""
Path selector — determines runtime path from task keywords.
"""

import re
from ledger.loader import Path_

HIGH_RISK_KEYWORDS = {
    "send", "publish", "post", "email", "tweet",
    "buy", "purchase", "transfer", "delete", "deploy",
    "launch", "sign", "charge",
}

STRUCTURED_KEYWORDS = {
    "plan", "design", "architect", "strategy", "roadmap",
    "refactor", "migrate", "build", "research",
}


def classify(task: str) -> Path_:
    words = set(re.findall(r"\w+", task.lower()))
    if words & HIGH_RISK_KEYWORDS:
        return "high_risk"
    if words & STRUCTURED_KEYWORDS:
        return "structured"
    if len(task) < 60 and task.count(".") < 2:
        return "fast"
    return "standard"