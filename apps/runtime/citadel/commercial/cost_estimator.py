"""Lightweight cost estimation for LLM providers.

Maps provider + model + token counts → projected cost in cents.
Extensible for new providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModelPricing:
    input_price_per_mtok: float
    output_price_per_mtok: float

    def estimate_cost_cents(self, input_tokens: int, output_tokens: int) -> int:
        input_cost = (input_tokens / 1_000_000) * self.input_price_per_mtok * 100
        output_cost = (output_tokens / 1_000_000) * self.output_price_per_mtok * 100
        return int(round(input_cost + output_cost))


ANTHROPIC_MODELS = {
    "claude-opus-4-7": ModelPricing(input_price_per_mtok=3.0, output_price_per_mtok=15.0),
    "claude-opus-4-6": ModelPricing(input_price_per_mtok=3.0, output_price_per_mtok=15.0),
    "claude-sonnet-4-6": ModelPricing(input_price_per_mtok=3.0, output_price_per_mtok=15.0),
    "claude-haiku-4-5": ModelPricing(input_price_per_mtok=0.8, output_price_per_mtok=4.0),
}

PROVIDERS = {
    "anthropic": ANTHROPIC_MODELS,
}


def estimate_cost(
    provider: Optional[str],
    model: Optional[str],
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> Optional[int]:
    """Estimate cost in cents for a provider + model + token count.

    Returns None if provider/model is unknown (caller must provide explicit cost).
    """
    if not provider or not model:
        return None

    provider_lower = provider.lower().strip()
    model_lower = model.lower().strip()

    if provider_lower not in PROVIDERS:
        return None

    models = PROVIDERS[provider_lower]
    if model_lower not in models:
        return None

    pricing = models[model_lower]
    return pricing.estimate_cost_cents(input_tokens, output_tokens)
