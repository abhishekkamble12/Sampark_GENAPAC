"""
Unit tests for agents.graph.supervisor_router covering all branching cases.

Branching logic:
    1. intake_error is set            → "error_response_node"
    2. validation.status == "low_confidence" → "low_confidence_node"
    3. issue.type is unknown           → normalised to "other", routes to "data_intelligence_node"
    4. happy path (known type, valid)  → "data_intelligence_node"
"""

from __future__ import annotations

import pytest

from agents.graph import supervisor_router
from agents.state import KNOWN_ISSUE_TYPES, GraphState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(
    issue_type: str = "road",
    validation_status: str = "valid",
    intake_error: str | None = None,
) -> GraphState:
    """Build a minimal GraphState for router testing."""
    return {
        "query": "test query",
        "user": {"user_id": "u1", "role": "citizen", "ward_ids": ["w1"], "preferred_channel": "email"},
        "issue": {
            "id": "iss_001",
            "type": issue_type,
            "location": {"lat": 18.52, "lng": 73.86, "address": "MG Road", "ward_id": "w1"},
            "description": "Test issue",
            "media_refs": [],
            "original_language": None,
            "severity": None,
        },
        "validation": {
            "duplicate": False,
            "confidence_score": 0.8,
            "status": validation_status,
            "location_verified": True,
            "failure_reason": None,
        },
        "context": None,
        "analytics": None,
        "prediction": None,
        "rag_chunks": None,
        "recommendation": None,
        "workflow": None,
        "response": None,
        "intake_error": intake_error,
        "translation_error": False,
        "extraction_error": False,
        "no_policy_context": False,
        "execution": {
            "session_id": "sess_test",
            "status": "running",
            "retry_count": 0,
            "node_checkpoints": [],
        },
    }


# ---------------------------------------------------------------------------
# Branch 1: intake_error is set
# ---------------------------------------------------------------------------

class TestIntakeErrorBranch:
    def test_audio_unprocessable_routes_to_error(self):
        state = _make_state(intake_error="audio_unprocessable")
        assert supervisor_router(state) == "error_response_node"

    def test_image_unclassifiable_routes_to_error(self):
        state = _make_state(intake_error="image_unclassifiable")
        assert supervisor_router(state) == "error_response_node"

    def test_any_intake_error_value_routes_to_error(self):
        state = _make_state(intake_error="unknown_error")
        assert supervisor_router(state) == "error_response_node"

    def test_intake_error_overrides_low_confidence(self):
        """intake_error check runs before validation status check."""
        state = _make_state(
            intake_error="audio_unprocessable",
            validation_status="low_confidence",
        )
        assert supervisor_router(state) == "error_response_node"


# ---------------------------------------------------------------------------
# Branch 2: validation.status == "low_confidence"
# ---------------------------------------------------------------------------

class TestLowConfidenceBranch:
    def test_low_confidence_routes_to_low_confidence_node(self):
        state = _make_state(validation_status="low_confidence")
        assert supervisor_router(state) == "low_confidence_node"

    def test_valid_status_does_not_trigger_low_confidence_branch(self):
        state = _make_state(validation_status="valid")
        result = supervisor_router(state)
        assert result != "low_confidence_node"


# ---------------------------------------------------------------------------
# Branch 3: unknown issue type → normalised to "other"
# ---------------------------------------------------------------------------

class TestUnknownIssueTypeBranch:
    def test_unknown_type_routes_to_data_intelligence(self):
        state = _make_state(issue_type="mystery_issue")
        result = supervisor_router(state)
        assert result == "data_intelligence_node"

    def test_unknown_type_is_normalised_to_other(self):
        state = _make_state(issue_type="mystery_issue")
        supervisor_router(state)
        assert state["issue"]["type"] == "other"  # type: ignore[index]

    def test_empty_string_type_is_normalised_to_other(self):
        state = _make_state(issue_type="")
        supervisor_router(state)
        assert state["issue"]["type"] == "other"  # type: ignore[index]


# ---------------------------------------------------------------------------
# Branch 4: happy path — known type, valid confidence
# ---------------------------------------------------------------------------

class TestHappyPath:
    @pytest.mark.parametrize("issue_type", sorted(KNOWN_ISSUE_TYPES))
    def test_known_types_route_to_data_intelligence(self, issue_type: str):
        state = _make_state(issue_type=issue_type)
        assert supervisor_router(state) == "data_intelligence_node"

    def test_road_type_routes_correctly(self):
        state = _make_state(issue_type="road")
        assert supervisor_router(state) == "data_intelligence_node"

    def test_flood_type_routes_correctly(self):
        state = _make_state(issue_type="flood")
        assert supervisor_router(state) == "data_intelligence_node"

    def test_other_type_routes_to_data_intelligence(self):
        """'other' is a known type and should NOT be re-normalised."""
        state = _make_state(issue_type="other")
        result = supervisor_router(state)
        assert result == "data_intelligence_node"
        assert state["issue"]["type"] == "other"  # type: ignore[index]

    def test_known_type_not_mutated(self):
        state = _make_state(issue_type="sanitation")
        supervisor_router(state)
        assert state["issue"]["type"] == "sanitation"  # type: ignore[index]
