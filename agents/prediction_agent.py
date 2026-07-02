"""
agents/prediction_agent.py — Prediction Agent for the Sampark AI Platform.

Implements heuristic risk forecasting models (flood, road deterioration),
ARIMA(7,1,1) volume forecasting mock, and SHAP-based explainability.
"""

from __future__ import annotations

import asyncio
import logging
import math
from typing import Any, Callable, Coroutine
from datetime import datetime, timedelta, timezone

from agents.state import GraphState, PredictionResult

logger = logging.getLogger(__name__)

_SLA_SECONDS = 15.0

def make_prediction_node() -> Callable[[GraphState], Coroutine[Any, Any, GraphState]]:
    """Return an async prediction_node function."""

    async def prediction_node(state: GraphState) -> GraphState:
        result: PredictionResult = {
            "flood_risk": None,
            "road_risk": None,
            "volume_forecast": None,
            "high_risk_alert": False,
            "error": None,
            "explainability": None,
        }

        analytics = state.get("analytics")
        context = state.get("context") or {}
        weather = context.get("weather")
        traffic = context.get("traffic") or {}
        historical_issues = context.get("historical_issues") or []

        # 8.2 Guard condition
        if not analytics or not weather:
            result["error"] = "insufficient_context"
            state["prediction"] = result
            return state

        try:
            async with asyncio.timeout(_SLA_SECONDS):
                
                # --- Feature Extraction ---
                rainfall_48h = float(weather.get("rainfall_forecast_48h", 0.0))
                
                # We mock missing complex features for the prototype
                drainage_capacity = 50.0
                slope = 5.0
                
                now = datetime.now(timezone.utc)
                d30 = now - timedelta(days=30)
                
                flood_count = 0
                pothole_count_30d = 0
                total_7d_volume = 0
                
                for row in historical_issues:
                    dt_str = row.get("reported_at")
                    try:
                        if isinstance(dt_str, str):
                            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                        elif isinstance(dt_str, datetime):
                            dt = dt_str
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                        else:
                            dt = now
                    except ValueError:
                        dt = now
                    
                    if row.get("type") == "flood":
                        flood_count += 1
                    
                    if dt >= d30 and row.get("type") == "road":
                        pothole_count_30d += 1
                        
                    if dt >= (now - timedelta(days=7)):
                        total_7d_volume += 1
                        
                rainfall_7d = float(weather.get("rainfall_past_7d", 10.0)) # mock
                road_age = 5.0 # mock
                
                traffic_density_str = traffic.get("traffic_density", "medium").lower()
                traffic_multiplier = {"high": 1.5, "medium": 1.0, "low": 0.5}.get(traffic_density_str, 1.0)
                
                # --- 8.3 Flood Risk (Logistic Regression Mock) ---
                # Logit: w1*rain + w2*flood_count - w3*drainage + w4*slope
                flood_logit = (0.2 * rainfall_48h) + (0.5 * flood_count) - (0.1 * drainage_capacity) + (0.2 * slope)
                flood_risk = 1.0 / (1.0 + math.exp(-max(-10, min(10, flood_logit / 5.0))))
                
                # --- 8.4 Road Risk (Gradient Boosting Mock) ---
                # Non-linear heuristic combo
                road_score = (pothole_count_30d * 0.05) + (rainfall_7d * 0.02) + (road_age * 0.05) + (traffic_multiplier * 0.1)
                road_risk = max(0.0, min(1.0, road_score))
                
                result["flood_risk"] = flood_risk
                result["road_risk"] = road_risk
                
                # --- 8.6 High Risk Alert ---
                if flood_risk > 0.75 or road_risk > 0.75:
                    result["high_risk_alert"] = True
                    
                # --- 8.7 SHAP Explainability ---
                # Determine which risk is higher to explain
                if flood_risk >= road_risk:
                    factors = {
                        "rainfall_forecast_48h": abs(0.2 * rainfall_48h),
                        "historical_flood_count": abs(0.5 * flood_count),
                        "drainage_capacity": abs(-0.1 * drainage_capacity),
                        "slope": abs(0.2 * slope)
                    }
                else:
                    factors = {
                        "pothole_count_30d": abs(pothole_count_30d * 0.05),
                        "rainfall_7d": abs(rainfall_7d * 0.02),
                        "road_age": abs(road_age * 0.05),
                        "traffic_density": abs(traffic_multiplier * 0.1)
                    }
                    
                total_weight = sum(factors.values())
                if total_weight == 0:
                    total_weight = 1.0 # prevent div by zero
                    
                sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)
                top_3 = sorted_factors[:3]
                
                # Normalize top 3 so they sum to exactly 100
                top_3_sum = sum(w for _, w in top_3)
                if top_3_sum == 0:
                    top_3_sum = 1.0
                    
                explainability = []
                for factor, weight in top_3:
                    pct = (weight / top_3_sum) * 100.0
                    explainability.append({"factor": factor, "weight_pct": pct})
                    
                result["explainability"] = explainability
                
                # --- 8.5 ARIMA(7,1,1) Volume Forecast Mock ---
                # Project 7 days forward using recent volume and 7d trend
                trend = analytics.get("trend_7d")
                if trend is None:
                    trend = 0.0
                
                daily_base = total_7d_volume / 7.0
                daily_trend = (trend / 100.0) / 7.0
                
                forecast = []
                for i in range(1, 8):
                    projected_vol = max(0, int(daily_base * (1 + (daily_trend * i))))
                    forecast_date = (now + timedelta(days=i)).strftime("%Y-%m-%d")
                    forecast.append({"date": forecast_date, "predicted_count": projected_vol})
                    
                result["volume_forecast"] = forecast

        except (TimeoutError, asyncio.TimeoutError):
            logger.warning("prediction_node SLA exceeded (%ds)", _SLA_SECONDS)
            # Retain partial results if any, but ensure fields aren't completely broken
            if result["error"] is None and result["explainability"] is None:
                 result["error"] = "timeout"
        except Exception:
            logger.exception("prediction_node encountered an error")
            result["error"] = "internal_error"

        state["prediction"] = result
        return state

    return prediction_node
