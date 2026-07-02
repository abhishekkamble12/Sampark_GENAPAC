"""
Property-based tests for agents.graph.supervisor_router.

Property: for any valid GraphState, supervisor_router always returns one of
the known node names — never an unexpected string.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from agents.graph import supervisor_router
from agents.state import KNOWN_ISSUE_TYPES

# The complete set of node names the router may legally return
VALID_ROUTER_OUTPUTS = frozenset(
    {"error_response_node", "low_confidence_node", "data_intelligence_node"}
)

# All issue types including unknown ones
_issue_types = st.one_of(
    st.sampled_from(sorted(KNOWN_ISSUE_TYPES)),
    st.text(min_size=0, max_size=30),  # arbitrary / unknown types
)

_validation_statuses = st.sampled_from(["valid", "low_confidence", "unknown_status"])

_intake_errors = st.one_of(
    st.none(),
    st.sampled_from(["audio_unprocessable", "image_unclassifiable"]),
    st.text(min_size=1, max_size=20),
)


def _build_state(issue_type: str, validation_status: str, intake_error: str | None) -> dict:
    return {
        "query": "test",
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
            "confidence_score": 0.5,
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
            "session_id": "sess_pbt",
            "status": "running",
            "retry_count": 0,
            "node_checkpoints": [],
        },
    }


@given(
    issue_type=_issue_types,
    validation_status=_validation_statuses,
    intake_error=_intake_errors,
)
@settings(max_examples=300)
def test_supervisor_router_always_returns_known_node(
    issue_type: str, validation_status: str, intake_error: str | None
) -> None:
    """supervisor_router must always return a member of VALID_ROUTER_OUTPUTS."""
    state = _build_state(issue_type, validation_status, intake_error)
    result = supervisor_router(state)
    assert result in VALID_ROUTER_OUTPUTS, (
        f"supervisor_router returned unexpected node {result!r} "
        f"for issue_type={issue_type!r}, validation_status={validation_status!r}, "
        f"intake_error={intake_error!r}"
    )


@given(
    issue_type=_issue_types,
    validation_status=_validation_statuses,
    intake_error=_intake_errors,
)
@settings(max_examples=200)
def test_issue_type_always_valid_after_routing(
    issue_type: str, validation_status: str, intake_error: str | None
) -> None:
    """After routing, issue.type is always a member of KNOWN_ISSUE_TYPES."""
    state = _build_state(issue_type, validation_status, intake_error)
    supervisor_router(state)
    assert state["issue"]["type"] in KNOWN_ISSUE_TYPES, (  # type: ignore[index]
        f"issue.type={state['issue']['type']!r} is not a known issue type"  # type: ignore[index]
    )
