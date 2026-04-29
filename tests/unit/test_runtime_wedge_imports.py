from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_default_app_factory_does_not_import_archived_ops_scaffolding():
    app_factory = (ROOT / "apps/runtime/citadel/api/__init__.py").read_text(
        encoding="utf-8"
    )

    forbidden_terms = [
        "citadel.sre",
        "setup_telemetry",
        "CommercialMiddleware",
        "opentelemetry",
    ]
    for term in forbidden_terms:
        assert term not in app_factory


def test_tenant_middleware_has_no_telemetry_dependency():
    middleware = (
        ROOT / "apps/runtime/citadel/middleware/fastapi_middleware.py"
    ).read_text(encoding="utf-8")

    assert "citadel.utils.telemetry" not in middleware
    assert "opentelemetry" not in middleware


def test_ops_scaffolding_is_archived_not_active():
    archived_paths = [
        "archive/legacy/runtime/sre",
        "archive/legacy/runtime/utils/telemetry.py",
        "archive/legacy/monitoring",
        "archive/legacy/tests/unit/test_otel_persistent_queue.py",
    ]
    active_paths = [
        "apps/runtime/citadel/sre",
        "apps/runtime/citadel/utils/telemetry.py",
        "monitoring",
        "tests/unit/test_otel_persistent_queue.py",
    ]

    for path in archived_paths:
        assert (ROOT / path).exists(), f"{path} should preserve archived code"
    for path in active_paths:
        assert not (ROOT / path).exists(), f"{path} should not be active"


def test_broad_trust_policy_matrix_is_archived_not_exported():
    package_init = (ROOT / "apps/runtime/citadel/agent_identity/__init__.py").read_text(
        encoding="utf-8"
    )

    assert "TrustPolicyEngine" not in package_init
    assert not (ROOT / "apps/runtime/citadel/agent_identity/trust_policy.py").exists()
    assert (ROOT / "archive/legacy/runtime/agent_identity/trust_policy.py").exists()
    assert (ROOT / "archive/legacy/tests/unit/test_trust_policy.py").exists()


def test_broad_orchestration_and_monitoring_docs_are_archived():
    archived_paths = [
        "archive/legacy/docs/internal/ORCHESTRATION.md",
        "archive/legacy/docs/internal/PERFORMANCE_REVIEW.md",
        "archive/legacy/docs/internal/HARDENING_PASS_REPORT.md",
        "archive/legacy/tests/test_orchestration_performance.py",
        "archive/legacy/docs/public/guides/trust-architecture.md",
        "archive/legacy/docs/public/guides/monitoring-governance.md",
        "archive/legacy/docs/public/recipes/agent-capability-downgrade.md",
        "archive/legacy/docs/public/recipes/ai-output-verification.md",
        "archive/legacy/docs/ARCHITECTURE.md",
        "archive/legacy/docs/strategy/FORGE_ROADMAP.md",
        "archive/legacy/docs/strategy/VISION.md",
        "archive/legacy/docs/public/integrations/crewai.md",
        "archive/legacy/docs/public/integrations/openai-agents.md",
        "archive/legacy/docs/public/integrations/langgraph.md",
        "archive/legacy/docs/public/recipes/multi-agent-coordination.md",
    ]
    active_paths = [
        "docs/internal/ORCHESTRATION.md",
        "docs/internal/PERFORMANCE_REVIEW.md",
        "docs/internal/HARDENING_PASS_REPORT.md",
        "tests/test_orchestration_performance.py",
        "docs/public/guides/trust-architecture.md",
        "docs/public/guides/monitoring-governance.md",
        "docs/public/recipes/agent-capability-downgrade.md",
        "docs/public/recipes/ai-output-verification.md",
        "docs/FORGE_ROADMAP.md",
        "docs/VISION.md",
        "docs/public/integrations/crewai.md",
        "docs/public/integrations/openai-agents.md",
        "docs/public/integrations/langgraph.md",
        "docs/public/recipes/multi-agent-coordination.md",
    ]

    for path in archived_paths:
        assert (ROOT / path).exists(), f"{path} should preserve archived material"
    for path in active_paths:
        assert not (ROOT / path).exists(), f"{path} should not be active"


def test_orchestration_runtime_is_labeled_compatibility_only():
    runtime = (ROOT / "apps/runtime/citadel/execution/orchestration.py").read_text(
        encoding="utf-8"
    )
    router = (ROOT / "apps/runtime/citadel/api/routers/orchestration.py").read_text(
        encoding="utf-8"
    )

    assert "Compatibility-only orchestration runtime" in runtime
    assert "Compatibility-only orchestration router" in router
    assert 'tags=["compatibility: orchestration"]' in router
    assert (ROOT / "apps/runtime/citadel/compatibility.py").exists()


def test_python_sdk_broad_helpers_are_compatibility_only_exports():
    sdk_init = (ROOT / "packages/sdk-python/citadel_governance/__init__.py").read_text(
        encoding="utf-8"
    )
    compatibility = (
        ROOT / "packages/sdk-python/citadel_governance/compatibility.py"
    ).read_text(encoding="utf-8")

    broad_exports = [
        "create_agent",
        "create_policy",
        "get_stats",
        "get_metrics_summary",
        "evaluate_all_trust_scores",
    ]
    for name in broad_exports:
        assert f'"{name}"' not in sdk_init
        assert f'"{name}"' in compatibility

    assert '"compatibility"' in sdk_init


def test_compatibility_guide_documents_public_boundaries():
    guide = (ROOT / "docs/COMPATIBILITY.md").read_text(encoding="utf-8")

    required_terms = [
        "citadel_governance.compatibility",
        "citadel.compatibility",
        "/v1/orchestrate",
        "gt_cap_",
        "PROBATION",
        "HIGHLY_TRUSTED",
    ]
    for term in required_terms:
        assert term in guide


def test_pytest_cache_uses_project_local_writable_path():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'cache_dir = ".pytest_cache_citadel"' in pyproject
    assert 'addopts = "-p no:cacheprovider"' in pyproject
    assert "[tool.ruff.lint]" in pyproject
