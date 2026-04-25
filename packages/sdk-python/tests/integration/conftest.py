"""Integration test configuration.

These tests require a live Citadel backend. They are skipped by default.

To run:
    export CITADEL_TEST_URL=https://ledger-sdk.fly.dev
    export CITADEL_TEST_API_KEY=your-key
    pytest tests/integration/ -v

Or use the Makefile:
    make integration
"""

import os

import pytest


@pytest.fixture(scope="session")
def base_url():
    url = os.getenv("CITADEL_TEST_URL")
    if not url:
        pytest.skip("CITADEL_TEST_URL not set — skipping integration tests")
    return url


@pytest.fixture(scope="session")
def api_key():
    key = os.getenv("CITADEL_TEST_API_KEY")
    if not key:
        pytest.skip("CITADEL_TEST_API_KEY not set — skipping integration tests")
    return key
