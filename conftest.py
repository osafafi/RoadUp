"""Root pytest configuration and shared fixtures.

Concrete fixtures (sample OpenDriveModel, a 4-way junction, a width-tapered road, a tiny network)
are added in the build session; see tests/fixtures/README.md for the intended set.
"""
from __future__ import annotations

# Intentionally empty for now. Shared `@pytest.fixture` definitions will live here so both
# co-located unit tests and tests/integration can request them by name.
