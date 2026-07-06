"""
agents/state.py — Shared LangGraph state schema for the Sampark AI Platform.

All LangGraph nodes share a single GraphState TypedDict. Each agent enriches
only its designated fields. Forward references are resolved at runtime via
`from __future__ import annotations`.
"""

from __future__ import annotations

from typing import List, Optional, TypedDict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNOWN_ISSUE_TYPES: frozenset[str] = frozenset(
    {"road", "sanitation", "water", "electricity", "flood", "traffic", "health", "other"}
)
"""The eight canonical issue categories understood by the platform."""

PRIORITY_LEVELS: frozenset[str] = frozenset({"Critical", "High", "Medium", "Low"})
"""Valid priority values for recommendations and workflow tasks."""


# ---------------------------------------------------------------------------
# Nested result types
# ---------------------------------------------------------------------------


class IssueObject(TypedDict):
    """Structured representation of a citizen-reported community issue.

    Produced by the Intake Agent and carried unchanged through the pipeline.

    Fields:
        id: Unique issue identifier (e.g. ``"iss_abc"``).
        type: One of the eight canonical categories defined in
            :data:`KNOWN_ISSUE_TYPES`.
        location: Optional geographic context ``{lat, lng, address, ward_id}``.
        description: Human-readable description of the issue.
        media_refs: List of Cloud Storage URIs for attached images/audio.
        original_language: BCP-47 language tag of the raw submission, if
            non-English (e.g. ``"hi"`` for Hindi).
        severity: Qualitative severity label, e.g. ``"High"``.  May be
            ``None`` when not determinable from the intake data.
    """

    id: str
    type: str  # road | sanitation | water | electricity | flood | traffic | health | other
    location: Optional[dict]  # {lat, lng, address, ward_id}
    description: str
    media_refs: List[str]  # Cloud Storage URIs
    original_language: Optional[str]
    severity: Optional[str]


class ValidationResult(TypedDict):
    """Output of the Validation Agent's credibility-scoring step.

    Fields:
        duplicate: ``True`` if a corroborating open issue was found within
            500 m with the same type.
        confidence_score: Composite credibility score in ``[0.0, 1.0]``.
        status: ``"valid"`` when ``confidence_score >= 0.4``, otherwise
            ``"low_confidence"``.
        location_verified: ``True`` if the Maps Tool confirmed the address
            lies within the configured municipal boundary.
        failure_reason: Human-readable explanation when validation cannot
            complete normally (e.g. geocoding service unavailable).
    """

    duplicate: bool
    confidence_score: float  # 0.0–1.0
    status: str  # valid | low_confidence
    location_verified: bool
    failure_reason: Optional[str]
    weather_corroborated: Optional[bool]
    has_media: Optional[bool]



class AnalyticsResult(TypedDict):
    """Output of the Analytics Agent.

    Fields:
        trend_7d: Percentage change in complaint volume over the last 7 days
            vs. the preceding 7-day window.  ``None`` when
            ``insufficient_data`` is ``True`` or ``zero_baseline`` is ``True``.
        trend_30d: Same metric for a 30-day window.
        zero_baseline: ``True`` when the preceding comparison window had zero
            complaints, making percentage trend undefined.
        cluster_labels: DBSCAN cluster label per ward; ``None`` when
            clustering was skipped.
        cluster_centroids: List of ``{lat, lng}`` dicts representing cluster
            centroids; ``None`` when clustering was skipped.
        sentiment_score: Gemini sentiment score ∈ ``[-1.0, 1.0]`` over the
            last-30-day ward reports.  ``None`` if unavailable.
        outlier_flag: ``True`` if the combined z-score of
            ``confidence_score`` + complaint frequency exceeds 2.0 std dev.
        insufficient_data: ``True`` when fewer than 5 historical records are
            available for the ward+type combination; trend and cluster fields
            will be ``None``.
        health_score_unavailable: ``True`` when no ``community_scores`` row
            with ``computed_at`` within the last 25 h was found in BigQuery.
    """

    trend_7d: Optional[float]
    trend_30d: Optional[float]
    zero_baseline: bool
    cluster_labels: Optional[List[str]]
    cluster_centroids: Optional[List[dict]]
    sentiment_score: Optional[float]
    outlier_flag: bool
    insufficient_data: bool
    health_score_unavailable: bool


class PredictionResult(TypedDict):
    """Output of the Prediction Agent's risk-forecasting step.

    Fields:
        flood_risk: Logistic-regression flood risk score ∈ ``[0.0, 1.0]``.
            ``None`` when the guard condition fires (insufficient context).
        road_risk: Gradient-boosting road-deterioration risk ∈ ``[0.0, 1.0]``.
            ``None`` when the guard condition fires.
        volume_forecast: 7-day per-ward per-category complaint volume
            forecast as a list of ``{date, predicted_count}`` dicts.
            ``None`` when the guard condition fires.
        high_risk_alert: ``True`` when ``flood_risk > 0.75`` OR
            ``road_risk > 0.75``.
        error: Set to ``"insufficient_context"`` when analytics or weather
            context is ``None``.  ``None`` on success.
        explainability: Top-3 SHAP feature contributions as a list of
            ``{factor, weight_pct}`` dicts whose ``weight_pct`` values sum to
            100.  ``None`` when prediction did not run.
    """

    flood_risk: Optional[float]
    road_risk: Optional[float]
    volume_forecast: Optional[List[dict]]
    high_risk_alert: bool
    error: Optional[str]
    explainability: Optional[List[dict]]  # [{factor, weight_pct}]


class RecommendationResult(TypedDict):
    """Structured, policy-grounded recommendation produced by the
    Recommendation Agent.

    Fields:
        action: Short imperative sentence describing the recommended action
            (e.g. ``"Deploy road-repair crew to MG Road within 24 hours"``).
        priority: One of :data:`PRIORITY_LEVELS` — ``"Critical"``,
            ``"High"``, ``"Medium"``, or ``"Low"``.
        rationale: Detailed explanation referencing analytics and prediction
            findings.
        cited_policies: List of policy document names / section references
            that ground the recommendation.
        estimated_impact: Qualitative or quantitative impact statement
            (e.g. ``"Reduces flood incidents by ~30% based on 3-year data"``).
        disclaimer: Present only when ``no_policy_context`` is ``True``; warns
            that the recommendation is not grounded in retrieved policy
            documents.
        confidence_caveat: ``True`` when ``validation.status == "low_confidence"``
            and priority is ``"High"`` or ``"Critical"``.
        error: Set to ``"timeout"`` if the Supervisor timed out the agent
            after 20 s.  ``None`` on success.
    """

    action: str
    priority: str  # Critical | High | Medium | Low
    rationale: str
    cited_policies: List[str]
    estimated_impact: str
    disclaimer: Optional[str]
    confidence_caveat: bool
    error: Optional[str]


class WorkflowResult(TypedDict):
    """Output of the Workflow Agent — department assignment and task metadata.

    Fields:
        assigned_department: Name of the government department responsible for
            resolving the issue (see ``DEPARTMENT_MAP`` in
            ``agents/workflow_agent.py``).
        task_id: Firestore ``tasks/{task_id}`` document identifier.
        due_date: ISO 8601 UTC deadline string.  Computed from
            ``datetime.utcnow()`` plus the SLA window for the given priority:
            Critical = 24 h, High = 72 h, Medium/Low = 7 d.
        routing_fallback: ``True`` when the issue type was not found in the
            routing table and fell back to ``"Admin Review"``.
        workflow_error: ``True`` when the Firestore write failed twice
            (double retry) and the task could not be persisted.
    """

    assigned_department: str
    task_id: str
    due_date: str  # UTC ISO 8601
    routing_fallback: bool
    workflow_error: bool


class ExecutionMeta(TypedDict):
    """Pipeline execution metadata used for checkpointing and observability.

    Fields:
        session_id: Unique identifier for this pipeline run.  Used as the
            Firestore path prefix for checkpoint documents.
        status: Current execution state — ``"running"``, ``"completed"``, or
            ``"failed"``.
        retry_count: Number of node-level retries that have occurred across
            all nodes in this session.
        node_checkpoints: Ordered list of node names that have been
            successfully persisted to Firestore.
    """

    session_id: str
    status: str  # running | completed | failed
    retry_count: int
    node_checkpoints: List[str]


# ---------------------------------------------------------------------------
# Top-level graph state
# ---------------------------------------------------------------------------


class GraphState(TypedDict):
    """Shared state object passed between every LangGraph node.

    The Supervisor initialises this at the start of each pipeline run; each
    agent enriches only its designated slice and returns the updated state.
    All fields are optional except ``query``, ``user``, and ``execution``,
    which must be populated before the graph starts.

    Fields:
        query: Raw input from the citizen (text, base64 audio, or image
            metadata depending on the submission channel).
        user: Authenticated user context ``{user_id, role, ward_ids,
            preferred_channel}`` decoded from the JWT.
        issue: Populated by the Intake Agent after successful extraction.
        validation: Populated by the Validation Agent.
        context: Raw data context dict assembled by the Data Intelligence
            Agent from BigQuery, Weather, and Maps sources.
        analytics: Populated by the Analytics Agent.
        prediction: Populated by the Prediction Agent.
        rag_chunks: Top-5 policy document chunks retrieved by the RAG
            pipeline for the current issue.
        recommendation: Populated by the Recommendation Agent.
        workflow: Populated by the Workflow Agent.
        response: Final natural-language response string sent back to the
            citizen via the API Gateway.
        intake_error: Set by the Intake Agent on unrecoverable errors:
            ``"audio_unprocessable"`` or ``"image_unclassifiable"``.
        translation_error: ``True`` when the detected language could not be
            translated to English.
        extraction_error: ``True`` when the LLM extraction prompt could not
            determine the issue location.
        no_policy_context: ``True`` when Vector Search returned zero results
            above the 0.75 similarity threshold.
        execution: Always present; tracks session ID, status, retry count,
            and completed node checkpoints.
    """

    query: str
    user: dict  # {user_id, role, ward_ids, preferred_channel}
    issue: Optional[IssueObject]
    validation: Optional[ValidationResult]
    context: Optional[dict]  # raw output from DataIntelligenceAgent
    analytics: Optional[AnalyticsResult]
    prediction: Optional[PredictionResult]
    rag_chunks: Optional[List[dict]]
    recommendation: Optional[RecommendationResult]
    workflow: Optional[WorkflowResult]
    response: Optional[str]
    intake_error: Optional[str]
    translation_error: bool
    extraction_error: bool
    no_policy_context: bool
    execution: ExecutionMeta
