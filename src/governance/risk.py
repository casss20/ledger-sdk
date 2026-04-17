"""
Action classifier — determines risk level and approval requirement.
"""

from enum import Enum


class Risk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Approval(str, Enum):
    NONE = "none"
    SOFT = "soft"
    HARD = "hard"


MATRIX: dict[str, tuple[Risk, Approval]] = {
    "read": (Risk.LOW, Approval.NONE),
    "search": (Risk.LOW, Approval.NONE),
    "research": (Risk.LOW, Approval.SOFT),
    "draft": (Risk.LOW, Approval.NONE),
    "plan": (Risk.MEDIUM, Approval.NONE),
    "write_file": (Risk.MEDIUM, Approval.SOFT),
    "send_message": (Risk.HIGH, Approval.HARD),
    "publish": (Risk.HIGH, Approval.HARD),
    "purchase": (Risk.HIGH, Approval.HARD),
    "delete": (Risk.HIGH, Approval.HARD),
    "deploy": (Risk.HIGH, Approval.HARD),
}


def classify(action: str) -> tuple[Risk, Approval]:
    return MATRIX.get(action, (Risk.MEDIUM, Approval.HARD))