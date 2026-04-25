import hashlib
import hmac
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class TrustLevel(Enum):
    """Agent trust levels."""
    REVOKED = "revoked"
    UNVERIFIED = "unverified"
    STANDARD = "standard"
    TRUSTED = "trusted"
    HIGHLY_TRUSTED = "highly_trusted"


@dataclass
class TrustScore:
    """Computed trust score for an agent."""
    agent_id: str
    score: float  # 0.0 to 1.0
    level: TrustLevel
    factors: Dict[str, float] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "score": round(self.score, 3),
            "level": self.level.value,
            "factors": self.factors,
            "updated_at": self.updated_at.isoformat() + "Z",
        }


class TrustScorer:
    """
    Computes trust scores for agents based on behavior.
    
    Factors:
    - Age of identity (older = more trusted)
    - Verification status
    - Action success rate
    - Rate of actions (too fast = suspicious)
    - Kill switch history
    - Compliance violations
    - Human approvals required
    """
    
    def __init__(self, db_pool=None):
        self.db = db_pool
    
    @staticmethod
    def compute_score(
        verified: bool,
        health_score: int,
        quarantined: bool,
        actions_today: int,
        token_spend: int,
        token_budget: int,
        compliance_tags: list,
        created_at: datetime,
        failed_challenges: int = 0,
        challenge_count: int = 0,
    ) -> tuple[float, TrustLevel, Dict[str, float]]:
        """
        Synchronous trust score computation from raw data.
        
        Used by the agents router when it already has the identity
        and agent rows fetched from the database.
        
        Returns: (score: float, level: TrustLevel, factors: dict)
        """
        factors: Dict[str, float] = {}
        score = 0.0
        
        # Verification factor (0.25)
        if verified:
            score += 0.25
            factors["verification"] = 0.25
        else:
            factors["verification"] = 0.0
        
        # Age factor (0.02 per day, max 0.15)
        age_days = (datetime.utcnow() - created_at).days if created_at else 0
        age_bonus = min(age_days * 0.02, 0.15)
        score += age_bonus
        factors["age_days"] = age_days
        factors["age_bonus"] = age_bonus
        
        # Health factor (max 0.20)
        health_factor = (health_score / 100) * 0.20
        score += health_factor
        factors["health"] = health_factor
        
        # Quarantine penalty
        if quarantined:
            score -= 0.30
            factors["quarantine"] = -0.30
        else:
            factors["quarantine"] = 0.10
            score += 0.10
        
        # Action rate factor
        if actions_today > 1000:
            score -= 0.10
            factors["action_rate"] = -0.10
        elif actions_today > 100:
            factors["action_rate"] = 0.05
            score += 0.05
        else:
            factors["action_rate"] = 0.10
            score += 0.10
        
        # Compliance factor
        required_tags = {"gdpr", "hipaa", "soc2"}
        present = set(t.lower() for t in compliance_tags) & required_tags
        if present:
            score += 0.15
            factors["compliance"] = 0.15
        else:
            factors["compliance"] = -0.15
            score -= 0.15
        
        # Budget factor
        if token_budget > 0:
            budget_ratio = token_spend / token_budget
            if budget_ratio > 0.9:
                score -= 0.05
                factors["budget"] = -0.05
            else:
                factors["budget"] = 0.05
                score += 0.05
        else:
            factors["budget"] = 0.0
        
        # Challenge reliability
        if challenge_count > 0:
            fail_rate = failed_challenges / max(challenge_count, 1)
            if fail_rate > 0.5:
                score -= 0.05
                factors["challenge_reliability"] = -0.05
            else:
                factors["challenge_reliability"] = 0.05
                score += 0.05
        else:
            factors["challenge_reliability"] = 0.0
        
        # Clamp
        score = max(0.0, min(1.0, score))
        
        # Determine level
        if score >= 0.8:
            level = TrustLevel.HIGHLY_TRUSTED
        elif score >= 0.6:
            level = TrustLevel.TRUSTED
        elif score >= 0.4:
            level = TrustLevel.STANDARD
        elif score >= 0.2:
            level = TrustLevel.UNVERIFIED
        else:
            level = TrustLevel.REVOKED
        
        return score, level, factors
    
    async def calculate_score(self, agent_id: str) -> TrustScore:
        """Calculate trust score for an agent (async, DB-backed)."""
        factors = {}
        
        if not self.db:
            return TrustScore(agent_id=agent_id, score=0.0, level=TrustLevel.REVOKED)
        
        async with self.db.acquire() as conn:
            # Get identity
            identity = await conn.fetchrow(
                "SELECT * FROM agent_identities WHERE agent_id = $1",
                agent_id
            )
            
            if not identity:
                return TrustScore(agent_id=agent_id, score=0.0, level=TrustLevel.REVOKED)
            
            # Factor 1: Verification status
            if identity["verification_status"] == "verified":
                factors["verification"] = 0.25
            elif identity["verification_status"] == "pending":
                factors["verification"] = 0.10
            else:
                factors["verification"] = 0.0
            
            # Factor 2: Identity age
            age_days = (datetime.utcnow() - identity["created_at"]).days
            if age_days > 30:
                factors["age"] = 0.15
            elif age_days > 7:
                factors["age"] = 0.10
            elif age_days > 1:
                factors["age"] = 0.05
            else:
                factors["age"] = 0.02
            
            # Factor 3: Action success rate (from agents table)
            agent = await conn.fetchrow(
                "SELECT * FROM agents WHERE agent_id = $1",
                agent_id
            )
            
            if agent:
                actions_today = agent.get("actions_today", 0)
                health_score = agent.get("health_score", 100)
                quarantined = agent.get("quarantined", False)
                
                # Health score factor
                factors["health"] = (health_score / 100.0) * 0.20
                
                # Quarantine penalty
                if quarantined:
                    factors["quarantine"] = -0.30
                else:
                    factors["quarantine"] = 0.10
                
                # Action rate factor (too many = suspicious)
                if actions_today > 1000:
                    factors["action_rate"] = -0.10
                elif actions_today > 100:
                    factors["action_rate"] = 0.05
                else:
                    factors["action_rate"] = 0.10
            else:
                factors["health"] = 0.0
                factors["quarantine"] = 0.0
                factors["action_rate"] = 0.0
            
            # Factor 4: No recent violations (check audit log)
            violations = await conn.fetchval(
                """
                SELECT COUNT(*) FROM audit_log
                WHERE actor = $1
                AND action LIKE '%violation%'
                AND created_at > NOW() - INTERVAL '7 days'
                """,
                agent_id
            )
            
            if violations == 0:
                factors["compliance"] = 0.15
            elif violations < 3:
                factors["compliance"] = 0.05
            else:
                factors["compliance"] = -0.15
            
            # Factor 5: Token budget adherence
            if agent:
                token_spend = agent.get("token_spend", 0)
                token_budget = agent.get("token_budget", 100000)
                if token_budget > 0:
                    budget_ratio = token_spend / token_budget
                    if budget_ratio < 0.5:
                        factors["budget"] = 0.05
                    elif budget_ratio < 0.9:
                        factors["budget"] = 0.02
                    else:
                        factors["budget"] = -0.05
                else:
                    factors["budget"] = 0.0
        
        # Calculate total score
        score = sum(factors.values())
        score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
        
        # Determine trust level
        if score >= 0.8:
            level = TrustLevel.HIGHLY_TRUSTED
        elif score >= 0.6:
            level = TrustLevel.TRUSTED
        elif score >= 0.4:
            level = TrustLevel.STANDARD
        elif score >= 0.2:
            level = TrustLevel.UNVERIFIED
        else:
            level = TrustLevel.REVOKED
        
        return TrustScore(
            agent_id=agent_id,
            score=score,
            level=level,
            factors=factors,
        )
    
    async def update_trust_level(self, agent_id: str) -> TrustScore:
        """Calculate and update an agent's trust level."""
        score = await self.calculate_score(agent_id)
        
        if not self.db:
            return score
        
        async with self.db.acquire() as conn:
            await conn.execute(
                """
                UPDATE agent_identities
                SET trust_level = $2,
                    metadata = jsonb_set(
                        jsonb_set(COALESCE(metadata, '{}'), '{trust_score}', $3),
                        '{trust_factors}', $4
                    ),
                    updated_at = NOW()
                WHERE agent_id = $1
                """,
                agent_id,
                score.level.value,
                str(score.score),
                str(score.factors),
            )
        
        return score
    
    async def get_trust_score(self, agent_id: str) -> Optional[TrustScore]:
        """Get the current trust score for an agent."""
        return await self.calculate_score(agent_id)
    
    async def evaluate_all(self) -> Dict[str, TrustScore]:
        """Evaluate trust scores for all agents."""
        if not self.db:
            return {}
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch("SELECT agent_id FROM agents")
        
        scores = {}
        for row in rows:
            scores[row["agent_id"]] = await self.update_trust_level(row["agent_id"])
        
        return scores
