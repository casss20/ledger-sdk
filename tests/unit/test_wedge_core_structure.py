from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_archived_non_wedge_surfaces_are_not_active_paths():
    archived_moves = {
        "apps/dashboard-demo": "archive/legacy/apps/dashboard-demo",
        "packages/sdk-typescript": "archive/legacy/packages/sdk-typescript",
        "docs/sre": "archive/legacy/docs/sre",
        "docs/agt": "archive/research/agt",
    }

    for active_path, archived_path in archived_moves.items():
        assert not (ROOT / active_path).exists(), f"{active_path} should stay archived"
        assert (ROOT / archived_path).exists(), f"{archived_path} should preserve the old files"


def test_active_core_manifest_stays_wedge_focused():
    manifest = (ROOT / "citadel-core" / "MANIFEST.md").read_text(encoding="utf-8")
    active_section = manifest.split("## Archived This Pass", maxsplit=1)[0]

    required_terms = [
        "cost_controls.py",
        "governance_decisions",
        "governance_audit_log",
        "gt_cap_",
    ]
    for term in required_terms:
        assert term in active_section

    forbidden_active_terms = [
        "dashboard-demo",
        "sdk-typescript",
        "docs/sre",
        "docs/agt",
    ]
    for term in forbidden_active_terms:
        assert term not in active_section
