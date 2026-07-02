"""
functions/health_score.py — Community Health Score Service (Task 14).

Computes aggregated health scores, handles weight rebalancing for missing data,
detects at-risk transitions, and simulates BigQuery metric sync.

Cloud Scheduler trigger command (run daily at 00:00 UTC):
gcloud scheduler jobs create pubsub health-score-job \
  --schedule="0 0 * * *" \
  --topic=trigger-health-score \
  --message-body="trigger"
"""

import logging

logger = logging.getLogger(__name__)

BASE_WEIGHTS = {
    "roads": 0.4,
    "flooding": 0.4,
    "sanitation": 0.2
}

def compute_health_score(sub_scores: dict[str, float]) -> float:
    """
    14.1 Dynamically rebalance weights if any sub-score is missing,
    maintaining the proportional ratios of the remaining weights.
    """
    available_keys = [k for k in sub_scores.keys() if k in BASE_WEIGHTS and sub_scores[k] is not None]
    
    if not available_keys:
        return 0.0
        
    total_available_weight = sum(BASE_WEIGHTS[k] for k in available_keys)
    
    rebalanced_weights = {
        k: BASE_WEIGHTS[k] / total_available_weight 
        for k in available_keys
    }
    
    final_score = sum(sub_scores[k] * rebalanced_weights[k] for k in available_keys)
    # Clamp bounding mathematically
    return max(0.0, min(100.0, final_score))

def detect_transitions(previous_score: float, current_score: float) -> tuple[bool, bool]:
    """
    14.3 Detect transition crossing 60 threshold.
    Returns (is_transition, is_at_risk_now)
    """
    prev_risk = previous_score < 60.0
    curr_risk = current_score < 60.0
    
    is_transition = prev_risk != curr_risk
    return is_transition, curr_risk

async def update_health_scores(ward_id: str, bq_client, pubsub_client, cache):
    """
    14.2, 14.4, 14.5 Orchestrate BigQuery derivation, calculation, and publishing.
    """
    try:
        # 14.2 Mock BQ aggregation
        sub_scores = await bq_client.get_90d_sub_scores(ward_id)
        current_score = compute_health_score(sub_scores)
    except Exception:
        logger.exception("Failed to compute sub-scores for ward %s", ward_id)
        return

    # Fallback cache lookup
    previous_score = cache.get(ward_id, 100.0)
    
    is_transition, is_at_risk = detect_transitions(previous_score, current_score)
    
    if is_transition:
        # 14.4 Publish Pub/Sub event
        try:
            payload = {
                "ward_id": ward_id, 
                "at_risk": is_at_risk, 
                "score": current_score,
                "previous_score": previous_score
            }
            await pubsub_client.publish("health-score-updated", payload)
        except Exception:
            logger.error("Failed to publish transition event for ward %s", ward_id)
            
    # 14.5 Write to BigQuery with fallback
    try:
        await bq_client.write_ward_health(ward_id, current_score, is_at_risk)
        # Update cache on success
        cache[ward_id] = current_score
    except Exception:
        logger.error("BigQuery write failed for ward %s. Falling back to cache.", ward_id)
        # We don't update cache so the next run tries to write the delta again
