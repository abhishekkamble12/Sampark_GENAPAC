"""
Property-based tests for agents.validation_agent — task 5.9.

Property: confidence_score always ∈ [0.0, 1.0] for any combination
of boolean evidence flags.
"""
from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from agents.validation_agent import _compute_confidence


@given(
    has_duplicate=st.booleans(),
    location_verified=st.booleans(),
    weather_corroborated=st.booleans(),
    has_media=st.booleans(),
)
@settings(max_examples=100)
def test_confidence_score_always_in_range(
    has_duplicate: bool,
    location_verified: bool,
    weather_corroborated: bool,
    has_media: bool,
) -> None:
    """confidence_score must always be in [0.0, 1.0]."""
    score = _compute_confidence(has_duplicate, location_verified, weather_corroborated, has_media)
    assert 0.0 <= score <= 1.0, (
        f"confidence_score={score} out of range for "
        f"duplicate={has_duplicate}, location_verified={location_verified}, "
        f"weather={weather_corroborated}, media={has_media}"
    )
