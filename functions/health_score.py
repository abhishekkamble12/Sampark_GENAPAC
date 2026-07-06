"""
functions/health_score.py — Community Health Score Service (FREE Stack)

Computes aggregated health scores using DuckDB analytics instead of BigQuery.
All data stored locally with zero cloud dependencies.

Replaces BigQuery with DuckDB (in-process, free).
"""

import logging

logger = logging.getLogger(__name__)

BASE_WEIGHTS = {"roads": 0.4, "flooding": 0.4, "sanitation": 0.2}


def compute_health_score(sub_scores: dict[str, float]) -> float:
    """Dynamically rebalance weights if any sub-score is missing."""
    available_keys = [
        k
        for k in sub_scores.keys()
        if k in BASE_WEIGHTS and sub_scores[k] is not None
    ]

    if not available_keys:
        return 0.0

    total_available_weight = sum(BASE_WEIGHTS[k] for k in available_keys)

    rebalanced_weights = {
        k: BASE_WEIGHTS[k] / total_available_weight for k in available_keys
    }

    final_score = sum(sub_scores[k] * rebalanced_weights[k] for k in available_keys)
    return max(0.0, min(100.0, final_score))


def detect_transitions(previous_score: float, current_score: float) -> tuple[bool, bool]:
    """Detect transition crossing 60 threshold.
    Returns (is_transition, is_at_risk_now).
    """
    prev_risk = previous_score < 60.0
    curr_risk = current_score < 60.0
    is_transition = prev_risk != curr_risk
    return is_transition, curr_risk


async def update_health_scores(ward_id: str, bq_client, pubsub_client, cache):
    """Orchestrate DuckDB derivation, calculation, and publishing.

    Replaces BigQuery with DuckDB for all analytical queries.
    """
    try:
        # Get sub-scores from DuckDB (replaces BigQuery)
        sub_scores = await bq_client.get_90d_sub_scores(ward_id)
        current_score = compute_health_score(sub_scores)
    except Exception:
        logger.exception("Failed to compute sub-scores for ward %s", ward_id)
        return

    # Fallback cache lookup
    previous_score = cache.get(ward_id, 100.0)

    is_transition, is_at_risk = detect_transitions(previous_score, current_score)

    if is_transition:
        # Publish event via local event queue (replaces Pub/Sub)
        try:
            payload = {
                "ward_id": ward_id,
                "at_risk": is_at_risk,
                "score": current_score,
                "previous_score": previous_score,
            }
            await pubsub_client.publish("health-score-updated", payload)
        except Exception:
            logger.error("Failed to publish transition event for ward %s", ward_id)

    # Write to DuckDB with fallback
    try:
        await bq_client.write_ward_health(ward_id, current_score, is_at_risk)
        cache[ward_id] = current_score
    except Exception:
        logger.error("DuckDB write failed for ward %s. Falling back to cache.", ward_id)
