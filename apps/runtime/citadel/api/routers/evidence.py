"""Evidence export router — regulator-ready decision bundles."""

from fastapi import APIRouter, Depends, HTTPException, status
from citadel.execution.kernel import Kernel
from citadel.api.dependencies import get_kernel
from citadel.audit_evidence import EvidenceExporter

router = APIRouter(prefix="/v1/audit", tags=["audit"])


@router.get("/evidence/{decision_id}")
async def export_decision_evidence(
    decision_id: str,
    kernel: Kernel = Depends(get_kernel),
):
    """Export a decision evidence bundle with audit chain and root hash.

    Returns a JSON bundle with:
    - decision record (status, winning_rule, reason, timestamps)
    - all audit events in chronological order
    - root hash (SHA256 over all events for tamper detection)

    Used for regulatory reporting and audit verification.
    """
    exporter = EvidenceExporter(kernel.repo)
    evidence = await exporter.export_decision(decision_id)

    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found",
        )

    return evidence.to_dict()


@router.post("/evidence/{decision_id}/verify")
async def verify_decision_evidence(
    decision_id: str,
    kernel: Kernel = Depends(get_kernel),
):
    """Verify the tamper-evidence of a decision bundle.

    Recomputes the root hash from all audit events and compares it to
    the stored root hash. Returns true if the evidence has not been
    modified since creation.
    """
    exporter = EvidenceExporter(kernel.repo)
    evidence = await exporter.export_decision(decision_id)

    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found",
        )

    is_valid = evidence.verify()
    return {
        "decision_id": str(evidence.decision_id),
        "verified": is_valid,
        "root_hash": evidence.root_hash,
        "event_count": len(evidence.audit_events),
    }
