"""Unit tests for Health Score Service (Task 14)."""

import pytest
from functions.health_score import compute_health_score, detect_transitions, update_health_scores

class _MockBQ:
    def __init__(self, fail_read=False, fail_write=False):
        self.fail_read = fail_read
        self.fail_write = fail_write
        self.written = []
    async def get_90d_sub_scores(self, ward_id):
        if self.fail_read:
            raise Exception("BQ Read Error")
        return {"roads": 50.0, "flooding": 80.0, "sanitation": 90.0}
    async def write_ward_health(self, ward_id, score, at_risk):
        if self.fail_write:
            raise Exception("BQ Write Error")
        self.written.append((ward_id, score, at_risk))

class _MockPubSub:
    def __init__(self):
        self.published = []
    async def publish(self, topic, payload):
        self.published.append((topic, payload))

def test_weight_rebalancing():
    # All present
    assert compute_health_score({"roads": 100, "flooding": 100, "sanitation": 100}) == 100.0
    
    # Missing flooding (roads=0.4, sanitation=0.2)
    # Total available base weight = 0.6
    # Roads new weight = 0.4 / 0.6 = 2/3
    # Sanitation new weight = 0.2 / 0.6 = 1/3
    res1 = compute_health_score({"roads": 90, "sanitation": 60})
    expected1 = (90 * (2/3)) + (60 * (1/3))
    assert abs(res1 - expected1) < 1e-5
    
    # Missing all
    assert compute_health_score({}) == 0.0

def test_transition_detection():
    # Dropping below 60
    is_trans, at_risk = detect_transitions(65.0, 59.9)
    assert is_trans is True
    assert at_risk is True
    
    # Rising above 60
    is_trans2, at_risk2 = detect_transitions(55.0, 60.1)
    assert is_trans2 is True
    assert at_risk2 is False
    
    # No transition
    is_trans3, _ = detect_transitions(80.0, 90.0)
    assert is_trans3 is False

@pytest.mark.asyncio
async def test_update_health_scores_fallback():
    bq = _MockBQ(fail_write=True)
    pubsub = _MockPubSub()
    cache = {"w1": 100.0}
    
    # The BQ read returns 50, 80, 90. Score = 0.4*50 + 0.4*80 + 0.2*90 = 20 + 32 + 18 = 70.0
    # Prev was 100.0 -> no transition (both >= 60).
    await update_health_scores("w1", bq, pubsub, cache)
    
    # Write failed, so cache should remain 100.0
    assert cache["w1"] == 100.0
    assert len(bq.written) == 0
    assert len(pubsub.published) == 0
