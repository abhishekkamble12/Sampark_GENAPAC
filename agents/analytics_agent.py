"""
agents/analytics_agent.py — Analytics Agent for the Sampark AI Platform.

Computes trends, geospatial clustering, sentiment scoring, and outlier detection.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Coroutine

from agents.state import AnalyticsResult, GraphState

logger = logging.getLogger(__name__)

_SLA_SECONDS = 12.0

_SENTIMENT_PROMPT = """\
You are an expert sentiment analyzer.
Analyze the sentiment of the following community complaints reported over the last 30 days.
Respond with a JSON object in this exact format:
{{"sentiment_score": <float between -1.0 and 1.0>}}

Where -1.0 is extremely negative, 0.0 is neutral, and 1.0 is extremely positive.

Complaints:
{descriptions}
"""

def make_analytics_node(
    gemini_model: Any,
    bigquery_tool: Any,
) -> Callable[[GraphState], Coroutine[Any, Any, GraphState]]:
    """Return an async analytics_node with injected dependencies."""

    async def analytics_node(state: GraphState) -> GraphState:
        result: AnalyticsResult = {
            "trend_7d": None,
            "trend_30d": None,
            "zero_baseline": False,
            "cluster_labels": None,
            "cluster_centroids": None,
            "sentiment_score": None,
            "outlier_flag": False,
            "insufficient_data": False,
            "health_score_unavailable": False,
        }

        issue = state.get("issue")
        context = state.get("context") or {}
        validation = state.get("validation") or {}
        historical_issues = context.get("historical_issues")

        # If no historical issues, we can't do much
        if historical_issues is None or not isinstance(historical_issues, list):
            result["insufficient_data"] = True
            state["analytics"] = result
            return state

        # 7.2 Insufficient-data guard
        if len(historical_issues) < 5:
            result["insufficient_data"] = True
            state["analytics"] = result
            return state

        try:
            async with asyncio.timeout(_SLA_SECONDS):
                now = datetime.now(timezone.utc)
                
                # Pre-process historical data dates
                parsed_issues = []
                for row in historical_issues:
                    reported_at = row.get("reported_at")
                    if isinstance(reported_at, str):
                        try:
                            # Try ISO format
                            dt = datetime.fromisoformat(reported_at.replace("Z", "+00:00"))
                        except ValueError:
                            dt = now  # Fallback
                    elif isinstance(reported_at, datetime):
                        dt = reported_at
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                    else:
                        dt = now
                    parsed_issues.append({"row": row, "dt": dt})

                # 7.3 Trend computation
                d7 = now - timedelta(days=7)
                d14 = now - timedelta(days=14)
                d30 = now - timedelta(days=30)
                d60 = now - timedelta(days=60)

                count_0_7 = sum(1 for x in parsed_issues if d7 <= x["dt"] <= now)
                count_7_14 = sum(1 for x in parsed_issues if d14 <= x["dt"] < d7)
                count_0_30 = sum(1 for x in parsed_issues if d30 <= x["dt"] <= now)
                count_30_60 = sum(1 for x in parsed_issues if d60 <= x["dt"] < d30)

                if count_7_14 == 0 or count_30_60 == 0:
                    result["zero_baseline"] = True
                else:
                    result["trend_7d"] = ((count_0_7 - count_7_14) / count_7_14) * 100.0
                    result["trend_30d"] = ((count_0_30 - count_30_60) / count_30_60) * 100.0

                # 7.4 DBSCAN-based geospatial clustering (Pure Python implementation)
                pts = []
                for x in parsed_issues:
                    loc = x["row"].get("location") or {}
                    lat, lng = loc.get("lat"), loc.get("lng")
                    if lat is not None and lng is not None:
                        pts.append((lat, lng))

                if pts:
                    labels, centroids = _simple_dbscan(pts, eps=0.005, min_pts=3)
                    result["cluster_labels"] = labels
                    result["cluster_centroids"] = [{"lat": c[0], "lng": c[1]} for c in centroids]

                # 7.5 Gemini-based sentiment scoring
                recent_descs = [
                    str(x["row"].get("description", ""))
                    for x in parsed_issues if d30 <= x["dt"] <= now
                ]
                recent_descs = [d for d in recent_descs if d.strip()]
                
                if recent_descs and gemini_model:
                    # Truncate to avoid massive prompts
                    if len(recent_descs) > 50:
                        recent_descs = recent_descs[:50]
                    
                    prompt = _SENTIMENT_PROMPT.format(descriptions="\n".join(f"- {d}" for d in recent_descs))
                    try:
                        response = gemini_model.generate_content(prompt)
                        text = response.text if hasattr(response, "text") else str(response)
                        
                        # Extract JSON
                        match = re.search(r"\{.*?\}", text, re.DOTALL)
                        if match:
                            data = json.loads(match.group(0))
                            score = data.get("sentiment_score")
                            if isinstance(score, (int, float)):
                                result["sentiment_score"] = float(score)
                    except Exception:
                        logger.exception("Gemini sentiment scoring failed")

                # 7.6 Outlier detection
                # Combined z-score of confidence_score + complaint frequency > 2.0 std dev
                # Since we don't have citywide stats, we mock a baseline for the ward
                # Let's say baseline mean frequency for 30d is 10, stddev is 5.
                # And confidence mean is 0.5, stddev is 0.2.
                conf_score = validation.get("confidence_score", 0.5)
                z_conf = (conf_score - 0.5) / 0.2
                z_freq = (count_0_30 - 10) / 5.0
                combined_z = (z_conf + z_freq) / 2.0
                if combined_z > 2.0:
                    result["outlier_flag"] = True

                # 7.7 Community Health Score
                ward_id = ""
                if issue and issue.get("location"):
                    ward_id = issue["location"].get("ward_id", "")

                if ward_id and bigquery_tool:
                    score = await bigquery_tool.read_community_health_score(ward_id)
                    if score is None:
                        result["health_score_unavailable"] = True
                else:
                    result["health_score_unavailable"] = True

        except (TimeoutError, asyncio.TimeoutError):
            logger.warning("analytics_node SLA exceeded (%ds)", _SLA_SECONDS)
        except Exception:
            logger.exception("analytics_node encountered an error")

        state["analytics"] = result
        return state

    return analytics_node


def _simple_dbscan(points: list[tuple[float, float]], eps: float, min_pts: int) -> tuple[list[str], list[tuple[float, float]]]:
    """Extremely lightweight pure-Python DBSCAN for testing/prototyping."""
    n = len(points)
    labels = ["unassigned"] * n
    cluster_id = 0
    
    def dist(p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])
        
    def region_query(p_idx):
        return [i for i in range(n) if dist(points[p_idx], points[i]) <= eps]
        
    for i in range(n):
        if labels[i] != "unassigned":
            continue
            
        neighbors = region_query(i)
        if len(neighbors) < min_pts:
            labels[i] = "noise"
            continue
            
        cluster_id += 1
        curr_label = f"cluster_{cluster_id}"
        labels[i] = curr_label
        
        # Expand cluster
        seed_set = neighbors.copy()
        seed_set.remove(i)
        
        while seed_set:
            q = seed_set.pop(0)
            if labels[q] == "noise":
                labels[q] = curr_label
            if labels[q] != "unassigned":
                continue
            labels[q] = curr_label
            q_neighbors = region_query(q)
            if len(q_neighbors) >= min_pts:
                seed_set.extend(q_neighbors)
                
    # Calculate centroids
    centroids = []
    for cid in range(1, cluster_id + 1):
        c_label = f"cluster_{cid}"
        c_pts = [points[i] for i in range(n) if labels[i] == c_label]
        if c_pts:
            c_lat = sum(p[0] for p in c_pts) / len(c_pts)
            c_lng = sum(p[1] for p in c_pts) / len(c_pts)
            centroids.append((c_lat, c_lng))
            
    return labels, centroids
