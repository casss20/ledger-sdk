from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAPPING_DOC = ROOT / "docs" / "ARCHITECTURE_RESEARCH_MAP.md"
COMPLIANCE_DOC = ROOT / "docs" / "COMPLIANCE_MAPPING.md"

CANONICAL_IMPLEMENTATION_PATHS = (
    "apps/runtime/citadel/tokens/governance_token.py",
    "apps/runtime/citadel/tokens/token_vault.py",
    "apps/runtime/citadel/tokens/governance_decision.py",
    "apps/runtime/citadel/tokens/audit_trail.py",
    "apps/runtime/citadel/audit_service.py",
    "db/migrations/004_governance_audit.sql",
    "apps/runtime/citadel/dashboard/posture_score.py",
    "apps/runtime/citadel/dashboard/activity_stream.py",
    "apps/runtime/citadel/dashboard/approval_queue.py",
    "apps/runtime/citadel/dashboard/audit_explorer.py",
    "apps/runtime/citadel/dashboard/coverage_heatmap.py",
    "apps/runtime/citadel/dashboard/kill_switch_panel.py",
)

FORBIDDEN_DUPLICATE_FILE_STEMS = (
    # New token abstractions beyond gt_cap_ should integrate with governance_token.py.
    "gt_token_family",
    "ledger_token",
    "ledger_tokens",
    "governance_token_v2",
    "token_family",
    # New audit stores/provenance systems should integrate with audit_events/governance_audit_log.
    "audit_archive",
    "audit_store",
    "collector_hash_chain",
    "provenance_graph",
    "governance_provenance",
    # Dashboard report patterns should map to existing Citadel dashboard modules.
    "security_inbox",
    "audit_browser",
    "stop_button_panel",
    "governance_posture_score",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def repo_files() -> list[Path]:
    ignored_parts = {
        ".git",
        ".pytest_cache",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
    }
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file() and not any(part in ignored_parts for part in path.parts)
    ]


def normalized_repo_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def test_research_mapping_uses_existing_repo_names():
    content = read(MAPPING_DOC)

    for expected in (
        "gt_cap_",
        "governance_decisions",
        "governance_tokens",
        "audit_events",
        "governance_audit_log",
        "PostgreSQL RLS",
        "KillSwitch",
        "ActivityStreamService",
        "PostureScoreService",
        "AuditExplorerService",
    ):
        assert expected in content


def test_canonical_implementation_paths_exist():
    for repo_path in CANONICAL_IMPLEMENTATION_PATHS:
        assert (ROOT / repo_path).exists(), f"Canonical implementation missing: {repo_path}"


def test_research_mapping_defers_unsafe_duplicate_architecture():
    content = read(MAPPING_DOC)

    for deferred in (
        "S3 Object Lock",
        "Collector-level audit hash chaining",
        "New `gt_` token families",
        "A second audit store",
    ):
        assert deferred in content

    assert "Do not add a second `gt_` token model" in content
    assert "Do not route audit through telemetry collector by default" in content


def test_compliance_mapping_links_report_language_to_citadel_primitives():
    content = read(COMPLIANCE_DOC)

    assert "Research Claim Mapping" in content
    assert "`gt_cap_` capability tokens" in content
    assert "`audit_events` for action lifecycle" in content
    assert "`governance_audit_log` for decision/token/execution-gating evidence" in content
    assert "Telemetry collector is export-only; audit remains DB-backed" in content


def test_no_duplicate_research_abstraction_files_are_added():
    violations = []
    for path in repo_files():
        repo_path = normalized_repo_path(path)
        if repo_path.startswith("archive/"):
            continue
        stem = path.stem.lower().replace("-", "_")
        if any(forbidden == stem for forbidden in FORBIDDEN_DUPLICATE_FILE_STEMS):
            violations.append(repo_path)

    assert violations == []
