"""
Tests for Coverage Heatmap (Phase 2 Compliance).

Target: 4 tests passing.
"""

import pytest
from ledger.dashboard.coverage_heatmap import HeatmapGenerator, CoverageHeatmap, HeatmapCell


TENANT = "test_tenant"


class TestCoverageHeatmap:
    """Test coverage heatmap generation."""

    @pytest.mark.asyncio
    async def test_heatmap_has_all_cells(self, db_pool):
        """Heatmap contains all lifecycle stages x policy categories."""
        generator = HeatmapGenerator(db_pool)
        heatmap = await generator.generate(TENANT)

        expected_cells = len(generator.LIFECYCLE_STAGES) * len(generator.POLICY_CATEGORIES)
        assert len(heatmap.cells) == expected_cells

    @pytest.mark.asyncio
    async def test_cell_values_in_range(self, db_pool):
        """All cell coverage percentages are 0-100."""
        generator = HeatmapGenerator(db_pool)
        heatmap = await generator.generate(TENANT)

        for cell in heatmap.cells:
            assert 0 <= cell.coverage_percent <= 100
            assert cell.trend in ["up", "stable", "down"]

    @pytest.mark.asyncio
    async def test_total_coverage_calculated(self, db_pool):
        """Total coverage is average of all cells."""
        generator = HeatmapGenerator(db_pool)
        heatmap = await generator.generate(TENANT)

        assert 0 <= heatmap.total_coverage <= 100
        if heatmap.cells:
            expected_avg = sum(c.coverage_percent for c in heatmap.cells) // len(heatmap.cells)
            assert heatmap.total_coverage == expected_avg

    @pytest.mark.asyncio
    async def test_auditor_export_generated(self, db_pool):
        """Auditor export contains heatmap data."""
        generator = HeatmapGenerator(db_pool)

        for framework in ["eu_ai_act", "soc2", "hipaa"]:
            export = await generator.export_for_auditor(TENANT, framework)

            assert export.framework == framework
            assert export.tenant_id == TENANT
            assert export.heatmap is not None
            assert export.exported_at is not None
