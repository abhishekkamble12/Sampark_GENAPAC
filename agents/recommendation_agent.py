"""
agents/recommendation_agent.py — Recommendation Agent for Sampark AI Platform.

Orchestrates the RAG pipeline to generate grounded recommendations and applies
a heuristic priority matrix based on predicted risk and context parameters.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine

from agents.state import GraphState, RecommendationResult

logger = logging.getLogger(__name__)

_SLA_SECONDS = 20.0

def make_recommendation_node(
    retriever: Any, 
    generator: Any
) -> Callable[[GraphState], Coroutine[Any, Any, GraphState]]:
    """Return an async recommendation_node function."""

    async def recommendation_node(state: GraphState) -> GraphState:
        result: RecommendationResult = {
            "action": None,
            "priority": "Low",
            "rationale": None,
            "cited_policies": [],
            "estimated_impact": "Medium", # Mock impact default
            "confidence_caveat": False,
            "disclaimer": None,
            "error": None,
        }

        issue = state.get("issue") or {}
        context = state.get("context") or {}
        analytics = state.get("analytics") or {}
        prediction = state.get("prediction") or {}
        validation = state.get("validation") or {}

        try:
            async with asyncio.timeout(_SLA_SECONDS):
                # 1. Build RAG Query (10.2)
                issue_type = issue.get("type", "unknown")
                ward = issue.get("location", {}).get("ward_id", "unknown")
                
                # We could append analytics info, but let's keep the query focused for retrieval
                query = f"{issue_type} issues in ward {ward}"
                
                # 2. Retrieve Policy Context (10.2)
                chunks, no_policy = await retriever.retrieve(query)
                state["no_policy_context"] = no_policy
                state["rag_chunks"] = chunks

                # 3. Generate Recommendation (10.2)
                gen_data = await generator.generate_recommendation(query, chunks)
                
                result["action"] = gen_data.get("action")
                result["rationale"] = gen_data.get("rationale")
                result["cited_policies"] = gen_data.get("cited_policies", [])
                
                # 4. Implement Priority Matrix (10.3)
                flood_risk = prediction.get("flood_risk") or 0.0
                road_risk = prediction.get("road_risk") or 0.0
                traffic_density = context.get("traffic", {}).get("traffic_density", "medium").lower()
                
                priority = "Low"
                if flood_risk > 0.75 and road_risk > 0.75 and traffic_density == "high":
                    priority = "Critical"
                elif (flood_risk > 0.75 or road_risk > 0.75) or traffic_density == "high":
                    priority = "High"
                elif traffic_density == "medium":
                    priority = "Medium"
                    
                result["priority"] = priority
                
                # 5. Caveat Logic (10.4)
                if validation.get("status") == "low_confidence" and priority in ("Critical", "High"):
                    result["confidence_caveat"] = True
                    
                # 6. Disclaimer Logic (10.5)
                if no_policy_context := state.get("no_policy_context"):
                    result["disclaimer"] = "No relevant municipal policy documents found; recommendation relies on generic heuristic."

        except (TimeoutError, asyncio.TimeoutError):
            logger.warning("recommendation_node SLA exceeded (%ds)", _SLA_SECONDS)
            result["error"] = "timeout"
        except Exception as e:
            logger.exception("recommendation_node encountered an error")
            result["error"] = str(e)

        state["recommendation"] = result
        return state

    return recommendation_node
