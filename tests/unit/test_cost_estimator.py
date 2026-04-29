"""Cost estimation for LLM providers."""

import pytest

from citadel.commercial.cost_estimator import estimate_cost


def test_anthropic_opus_pricing():
    """Estimate Anthropic Opus cost from token counts."""
    cost = estimate_cost(
        provider="anthropic",
        model="claude-opus-4-7",
        input_tokens=1_000_000,
        output_tokens=500_000,
    )
    assert cost is not None
    input_cost = 1_000_000 / 1_000_000 * 3.0 * 100
    output_cost = 500_000 / 1_000_000 * 15.0 * 100
    expected = int(round(input_cost + output_cost))
    assert cost == expected


def test_anthropic_haiku_pricing():
    """Estimate Anthropic Haiku cost (cheaper model)."""
    cost = estimate_cost(
        provider="anthropic",
        model="claude-haiku-4-5",
        input_tokens=100_000,
        output_tokens=50_000,
    )
    assert cost is not None
    input_cost = 100_000 / 1_000_000 * 0.8 * 100
    output_cost = 50_000 / 1_000_000 * 4.0 * 100
    expected = int(round(input_cost + output_cost))
    assert cost == expected


def test_estimate_with_zero_tokens():
    """Zero token estimate returns zero cost."""
    cost = estimate_cost(
        provider="anthropic",
        model="claude-opus-4-7",
        input_tokens=0,
        output_tokens=0,
    )
    assert cost == 0


def test_unknown_provider_returns_none():
    """Unknown provider returns None so caller can provide explicit cost."""
    cost = estimate_cost(
        provider="unknown",
        model="gpt-4",
        input_tokens=1000,
        output_tokens=500,
    )
    assert cost is None


def test_unknown_model_returns_none():
    """Unknown model returns None."""
    cost = estimate_cost(
        provider="anthropic",
        model="claude-unknown",
        input_tokens=1000,
        output_tokens=500,
    )
    assert cost is None


def test_missing_provider_returns_none():
    """Missing provider returns None."""
    cost = estimate_cost(
        provider=None,
        model="claude-opus-4-7",
        input_tokens=1000,
        output_tokens=500,
    )
    assert cost is None


def test_case_insensitive_provider_and_model():
    """Provider and model names are case-insensitive."""
    cost = estimate_cost(
        provider="ANTHROPIC",
        model="CLAUDE-OPUS-4-7",
        input_tokens=1000,
        output_tokens=500,
    )
    assert cost is not None
    cost2 = estimate_cost(
        provider="anthropic",
        model="claude-opus-4-7",
        input_tokens=1000,
        output_tokens=500,
    )
    assert cost == cost2


def test_realistic_conversation_estimate():
    """Estimate cost for a realistic conversation."""
    cost = estimate_cost(
        provider="anthropic",
        model="claude-opus-4-7",
        input_tokens=10_000,
        output_tokens=2_000,
    )
    assert cost is not None
    input_cost = 10_000 / 1_000_000 * 3.0 * 100
    output_cost = 2_000 / 1_000_000 * 15.0 * 100
    expected = int(round(input_cost + output_cost))
    assert cost == expected
    assert cost > 0
