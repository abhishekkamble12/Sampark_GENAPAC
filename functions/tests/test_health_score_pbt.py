"""Property-based tests for Health Score Service (Task 14)."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from functions.health_score import compute_health_score

@given(
    st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
    st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
    st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
    st.booleans(),
    st.booleans(),
    st.booleans()
)
@settings(max_examples=100)
def test_compute_health_score_pbt(r_val, f_val, s_val, has_r, has_f, has_s):
    """14.9 compute_health_score always returns a value in [0.0, 100.0] and rebalanced weights logically sum to 1."""
    
    sub_scores = {}
    if has_r: sub_scores["roads"] = r_val
    if has_f: sub_scores["flooding"] = f_val
    if has_s: sub_scores["sanitation"] = s_val
    
    score = compute_health_score(sub_scores)
    
    # 1. Bounding check
    assert 0.0 <= score <= 100.0
    
    # 2. Logic check: if all active sub_scores are X, the result MUST be X 
    # (proving the weights dynamically sum exactly to 1.0)
    if sub_scores:
        uniform_scores = {k: 42.42 for k in sub_scores.keys()}
        uniform_res = compute_health_score(uniform_scores)
        assert abs(uniform_res - 42.42) < 1e-5
