"""
Ledger Output Schema — Standard typed output schemas for all agents.

Every agent produces one of these. The Ledger Router inspects the type
to decide approval level and routing.

OutputType     → Approval level
-----------      ---------------
RESEARCH       → SOFT  (informational, auto-queue)
LISTING        → HARD  (must not publish without approval)
ASSET          → HARD  (must not use without approval)
MESSAGE        → HARD  (must not send without approval)
TASK           → NONE  (internal orchestration, auto-proceed)
GENERIC        → HARD  (unknown — held for review)
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OutputType(str, Enum):
    RESEARCH = "research"
    LISTING = "listing"
    ASSET = "asset"
    MESSAGE = "message"
    TASK = "task"
    GENERIC = "generic"


class ApprovalLevel(str, Enum):
    NONE = "none"    # auto-proceed
    SOFT = "soft"    # queue for review, can auto-continue
    HARD = "hard"    # blocked until human explicitly approves


class AgentOutput(BaseModel):
    """Base output for all agent actions."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    output_type: OutputType
    agent_id: str
    agent_name: str
    room_id: Optional[str] = None
    task_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # Routing state — filled in by LedgerRouter
    target_channel: Optional[str] = None
    approval_level: ApprovalLevel = ApprovalLevel.HARD
    routed_at: Optional[str] = None
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None

    # Raw payload
    data: Dict[str, Any] = {}
    summary: str = ""


class Opportunity(BaseModel):
    """Research opportunity found by agent."""
    title: str
    niche: str
    demand_score: float  # 0.0 – 1.0
    competition: float   # 0.0 – 1.0
    fit_score: float     # 0.0 – 1.0
    reasoning: str
    keywords: List[str] = []
    estimated_price_range: Optional[str] = None


class ResearchOutput(AgentOutput):
    """Research output (e.g., Nova agent)."""
    output_type: OutputType = OutputType.RESEARCH
    approval_level: ApprovalLevel = ApprovalLevel.SOFT

    opportunities: List[Opportunity] = []
    top_pick: Optional[Opportunity] = None
    market_summary: str = ""
    niche_analyzed: str = ""


class ListingOutput(AgentOutput):
    """Listing output (e.g., Forge agent)."""
    output_type: OutputType = OutputType.LISTING
    approval_level: ApprovalLevel = ApprovalLevel.HARD

    title: str = ""
    description: str = ""
    tags: List[str] = []
    price: Optional[float] = None
    currency: str = "USD"
    sku: Optional[str] = None
    category: Optional[str] = None
    asset_ids: List[str] = []
    platform_hints: Dict[str, Any] = {}
    policy_passed: bool = False
    quality_score: Optional[float] = None


class AssetOutput(AgentOutput):
    """Asset output (e.g., Pixel agent)."""
    output_type: OutputType = OutputType.ASSET
    approval_level: ApprovalLevel = ApprovalLevel.HARD

    asset_type: str = "image"
    urls: List[str] = []
    prompt_used: str = ""
    style_notes: str = ""
    variants: int = 1


class ClassifiedMessage(BaseModel):
    """A classified message with draft reply."""
    original: str
    sender: Optional[str] = None
    category: str  # support | pre-sale | spam | complaint | praise | escalate
    priority: str  # low | medium | high | urgent
    draft_reply: Optional[str] = None
    sentiment: Optional[str] = None


class MessageOutput(AgentOutput):
    """Message output (e.g., Cipher agent)."""
    output_type: OutputType = OutputType.MESSAGE
    approval_level: ApprovalLevel = ApprovalLevel.HARD

    messages: List[ClassifiedMessage] = []
    high_priority_count: int = 0
    requires_reply_count: int = 0


class TaskOutput(AgentOutput):
    """Task output (e.g., Ultron agent)."""
    output_type: OutputType = OutputType.TASK
    approval_level: ApprovalLevel = ApprovalLevel.NONE

    subtasks_created: List[str] = []
    agents_dispatched: List[str] = []
    status_updates: List[str] = []
