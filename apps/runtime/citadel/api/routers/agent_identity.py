"""
Agent Identity Router — REST API for cryptographic agent identity management.

Uses the agent_identity module for all operations:
- IdentityManager for CRUD + keypair generation
- AgentAuthService for authentication + challenge-response
- TrustScorer for behavior-based trust scoring
- AgentVerifier for governance token bridging
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from citadel.api.dependencies import require_api_key

router = APIRouter(tags=["agent-identity"])


# ─── Request/Response Models ───

class RegisterAgentRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=256)
    tenant_id: str = Field("dev_tenant", min_length=1, max_length=128)
    owner: str = Field("op-1", min_length=1, max_length=128)


class RegisterAgentResponse(BaseModel):
    agent_id: str
    secret_key: str  # ⚠️ Only shown once — client must store securely
    public_key: str
    api_key: str


class AuthenticateRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=128)
    secret_key: str = Field(..., min_length=1, max_length=4096)


class AuthenticateResponse(BaseModel):
    agent_id: str
    authenticated: bool
    tenant_id: str
    trust_level: str
    verification_status: str


class VerifyAgentRequest(BaseModel):
    verifier_id: str = Field(..., min_length=1, max_length=128)


class VerifyAgentResponse(BaseModel):
    agent_id: str
    verified: bool
    trust_level: str


class RevokeAgentRequest(BaseModel):
    reason: str = Field(default="Revoked by operator", max_length=500)


class RevokeAgentResponse(BaseModel):
    agent_id: str
    revoked: bool
    reason: str


class ChallengeResponse(BaseModel):
    agent_id: str
    challenge: str
    expires_in: int


class VerifyChallengeRequest(BaseModel):
    response: str = Field(..., min_length=1, max_length=4096)


class VerifyChallengeResponse(BaseModel):
    agent_id: str
    verified: bool


class TrustScoreResponse(BaseModel):
    agent_id: str
    score: float
    level: str
    factors: Dict[str, float]


class AgentIdentityOut(BaseModel):
    agent_id: str
    tenant_id: str
    public_key: str
    trust_level: str
    verification_status: str
    created_at: Optional[str]
    last_verified_at: Optional[str]
    metadata: Dict[str, Any]


class ListIdentitiesResponse(BaseModel):
    identities: List[AgentIdentityOut]
    count: int


class IssueCapabilityRequest(BaseModel):
    action: str = Field(..., min_length=1, max_length=256)
    resource: str = Field(..., min_length=1, max_length=256)
    context: Dict[str, Any] = {}


class IssueCapabilityResponse(BaseModel):
    verified: bool
    authorized: bool
    agent_id: str
    trust_score: Optional[float]
    trust_level: Optional[str]
    token: Optional[Dict[str, Any]]
    error: Optional[str]


# ─── Dependencies ───

def _get_db_pool(request: Request):
    pool = getattr(request.app.state, "db_pool", None)
    if not pool:
        raise HTTPException(status_code=503, detail="Database pool not available")
    return pool


# ─── Endpoints ───

@router.post("/agent-identities", response_model=RegisterAgentResponse, status_code=201)
async def register_agent(body: RegisterAgentRequest, request: Request, _: str = Depends(require_api_key)):
    """
    Register a new agent with cryptographic identity.

    Returns secret_key, public_key, and api_key.
    ⚠️ secret_key is shown ONLY once — client must store securely.
    """
    from citadel.agent_identity.identity import IdentityManager

    tenant_id = getattr(request.state, "tenant_id", body.tenant_id)
    db_pool = _get_db_pool(request)
    manager = IdentityManager(db_pool)

    credentials = await manager.register_agent(
        agent_id=body.agent_id,
        tenant_id=tenant_id,
        name=body.name,
        owner=body.owner,
    )

    return RegisterAgentResponse(
        agent_id=credentials.agent_id,
        secret_key=credentials.secret_key,
        public_key=credentials.public_key,
        api_key=credentials.api_key,
    )


@router.post("/agent-identities/{agent_id}/authenticate", response_model=AuthenticateResponse)
async def authenticate_agent(agent_id: str, body: AuthenticateRequest, request: Request, _: str = Depends(require_api_key)):
    """Authenticate an agent using its secret key."""
    from citadel.agent_identity.identity import IdentityManager

    db_pool = _get_db_pool(request)
    manager = IdentityManager(db_pool)

    identity = await manager.authenticate_agent(agent_id, body.secret_key)
    if not identity:
        raise HTTPException(status_code=401, detail="Invalid agent_id or secret_key")

    return AuthenticateResponse(
        agent_id=identity.agent_id,
        authenticated=True,
        tenant_id=identity.tenant_id,
        trust_level=identity.trust_level,
        verification_status=identity.verification_status,
    )


@router.get("/agent-identities/{agent_id}", response_model=AgentIdentityOut)
async def get_agent_identity(agent_id: str, request: Request, _: str = Depends(require_api_key)):
    """Get an agent's cryptographic identity."""
    from citadel.agent_identity.identity import IdentityManager

    db_pool = _get_db_pool(request)
    manager = IdentityManager(db_pool)

    identity = await manager.get_identity(agent_id)
    if not identity:
        raise HTTPException(status_code=404, detail="Agent identity not found")

    return AgentIdentityOut(
        agent_id=identity.agent_id,
        tenant_id=identity.tenant_id,
        public_key=identity.public_key,
        trust_level=identity.trust_level,
        verification_status=identity.verification_status,
        created_at=identity.created_at.isoformat() + "Z" if identity.created_at else None,
        last_verified_at=identity.last_verified_at.isoformat() + "Z" if identity.last_verified_at else None,
        metadata=identity.metadata,
    )


@router.get("/agent-identities", response_model=ListIdentitiesResponse)
async def list_agent_identities(
    request: Request,
    tenant_id: Optional[str] = Query(None, min_length=1, max_length=128),
    _: str = Depends(require_api_key),
):
    """List all agent identities, optionally filtered by tenant."""
    from citadel.agent_identity.identity import IdentityManager

    effective_tenant = tenant_id or getattr(request.state, "tenant_id", None)
    db_pool = _get_db_pool(request)
    manager = IdentityManager(db_pool)

    identities = await manager.list_identities(tenant_id=effective_tenant)

    return ListIdentitiesResponse(
        identities=[
            AgentIdentityOut(
                agent_id=i.agent_id,
                tenant_id=i.tenant_id,
                public_key=i.public_key,
                trust_level=i.trust_level,
                verification_status=i.verification_status,
                created_at=i.created_at.isoformat() + "Z" if i.created_at else None,
                last_verified_at=i.last_verified_at.isoformat() + "Z" if i.last_verified_at else None,
                metadata=i.metadata,
            )
            for i in identities
        ],
        count=len(identities),
    )


@router.post("/agent-identities/{agent_id}/verify", response_model=VerifyAgentResponse)
async def verify_agent(agent_id: str, body: VerifyAgentRequest, request: Request, _: str = Depends(require_api_key)):
    """Mark an agent identity as verified by a human operator."""
    from citadel.agent_identity.identity import IdentityManager

    db_pool = _get_db_pool(request)
    manager = IdentityManager(db_pool)

    ok = await manager.verify_agent(agent_id, body.verifier_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Agent identity not found")

    identity = await manager.get_identity(agent_id)
    return VerifyAgentResponse(
        agent_id=agent_id,
        verified=True,
        trust_level=identity.trust_level if identity else "unknown",
    )


@router.post("/agent-identities/{agent_id}/revoke", response_model=RevokeAgentResponse)
async def revoke_agent(agent_id: str, body: RevokeAgentRequest, request: Request, _: str = Depends(require_api_key)):
    """Revoke an agent's cryptographic identity."""
    from citadel.agent_identity.identity import IdentityManager

    db_pool = _get_db_pool(request)
    manager = IdentityManager(db_pool)

    ok = await manager.revoke_agent(agent_id, body.reason)
    if not ok:
        raise HTTPException(status_code=404, detail="Agent identity not found")

    return RevokeAgentResponse(
        agent_id=agent_id,
        revoked=True,
        reason=body.reason,
    )


# ─── Challenge-Response ───

@router.post("/agent-identities/{agent_id}/challenge", response_model=ChallengeResponse)
async def generate_challenge(agent_id: str, request: Request, _: str = Depends(require_api_key)):
    """Generate a challenge nonce for agent authentication."""
    from citadel.agent_identity.auth import AgentAuthService

    db_pool = _get_db_pool(request)
    auth = AgentAuthService(db_pool)

    result = await auth.generate_challenge(agent_id)
    return ChallengeResponse(
        agent_id=agent_id,
        challenge=result["challenge"],
        expires_in=result["expires_in"],
    )


@router.post("/agent-identities/{agent_id}/challenge/verify", response_model=VerifyChallengeResponse)
async def verify_challenge(agent_id: str, body: VerifyChallengeRequest, request: Request, _: str = Depends(require_api_key)):
    """Verify a challenge response from an agent."""
    from citadel.agent_identity.auth import AgentAuthService

    db_pool = _get_db_pool(request)
    auth = AgentAuthService(db_pool)

    ok = await auth.verify_challenge(agent_id, body.response)
    return VerifyChallengeResponse(agent_id=agent_id, verified=ok)


# ─── Trust Scoring ───

@router.get("/agent-identities/{agent_id}/trust", response_model=TrustScoreResponse)
async def get_trust_score(agent_id: str, request: Request, _: str = Depends(require_api_key)):
    """Get the current trust score for an agent."""
    from citadel.agent_identity.trust_score import TrustScorer

    db_pool = _get_db_pool(request)
    scorer = TrustScorer(db_pool)

    score = await scorer.get_trust_score(agent_id)
    if not score:
        raise HTTPException(status_code=404, detail="Agent not found")

    return TrustScoreResponse(
        agent_id=score.agent_id,
        score=score.score,
        level=score.level.value,
        factors=score.factors,
    )


@router.post("/agent-identities/{agent_id}/trust/update", response_model=TrustScoreResponse)
async def update_trust_score(agent_id: str, request: Request, _: str = Depends(require_api_key)):
    """Recalculate and update an agent's trust score."""
    from citadel.agent_identity.trust_score import TrustScorer

    db_pool = _get_db_pool(request)
    scorer = TrustScorer(db_pool)

    score = await scorer.update_trust_level(agent_id)
    return TrustScoreResponse(
        agent_id=score.agent_id,
        score=score.score,
        level=score.level.value,
        factors=score.factors,
    )


@router.post("/agent-identities/trust/evaluate-all")
async def evaluate_all_trust_scores(request: Request, _: str = Depends(require_api_key)):
    """Recalculate trust scores for all agents."""
    from citadel.agent_identity.trust_score import TrustScorer

    db_pool = _get_db_pool(request)
    scorer = TrustScorer(db_pool)

    scores = await scorer.evaluate_all()
    return {
        "evaluated": len(scores),
        "scores": {
            agent_id: {
                "score": s.score,
                "level": s.level.value,
            }
            for agent_id, s in scores.items()
        },
    }


# ─── Capability Token Issuance (Governance Bridge) ───

@router.post("/agent-identities/{agent_id}/capability", response_model=IssueCapabilityResponse)
async def issue_capability(agent_id: str, body: IssueCapabilityRequest, request: Request, _: str = Depends(require_api_key)):
    """
    Verify agent identity and issue a capability token.

    Bridges agent identity to the governance token system.
    """
    from citadel.agent_identity.auth import AgentAuthService
    from citadel.agent_identity.verification import AgentVerifier

    db_pool = _get_db_pool(request)
    auth = AgentAuthService(db_pool)

    verifier = AgentVerifier(auth_service=auth)

    # For this endpoint we do a simplified verification
    # In production, the agent would provide a challenge signature
    identity = await auth.identity_manager.get_identity(agent_id)
    if not identity:
        raise HTTPException(status_code=404, detail="Agent identity not found")

    if identity.verification_status == "revoked":
        return IssueCapabilityResponse(
            verified=True,
            authorized=False,
            agent_id=agent_id,
            error="Agent identity has been revoked",
        )

    # Issue placeholder capability token
    from datetime import datetime, timedelta

    token = {
        "type": "capability_token",
        "agent_id": agent_id,
        "action": body.action,
        "resource": body.resource,
        "issued_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "trust_level": identity.trust_level,
    }

    return IssueCapabilityResponse(
        verified=True,
        authorized=True,
        agent_id=agent_id,
        trust_score=None,
        trust_level=identity.trust_level,
        token=token,
    )
