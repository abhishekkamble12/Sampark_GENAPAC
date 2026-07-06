"""
tools/bigquery_tool.py — DuckDB Analytics Tool (FREE replacement for BigQuery)

Provides in-process analytical queries using DuckDB instead of BigQuery.
All data stored locally with zero cloud dependencies.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any

import duckdb

logger = logging.getLogger(__name__)


class BigQueryTool:
    """DuckDB-powered analytics tool replacing BigQuery.

    All methods are async-compatible. DuckDB runs in-process with zero
    network calls and zero cost.
    """

    def __init__(self, project_id: str = "local", dataset: str = "sampark_analytics"):
        self._project_id = project_id
        self._dataset = dataset
        self._db_path = os.getenv("DUCKDB_PATH", "data/sampark_analytics.duckdb")
        self._conn: duckdb.DuckDBPyConnection | None = None

    def _ensure_conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            self._conn = duckdb.connect(self._db_path)
            self._init_tables()
        return self._conn

    def _init_tables(self) -> None:
        """Create tables if they don't exist (mirrors BigQuery schema)."""
        conn = self._conn
        conn.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                issue_id VARCHAR,
                type VARCHAR,
                ward_id VARCHAR,
                lat DOUBLE,
                lng DOUBLE,
                severity VARCHAR,
                status VARCHAR,
                reported_at TIMESTAMP,
                resolved_at TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS community_scores (
                ward_id VARCHAR,
                score_date DATE,
                infrastructure DOUBLE,
                sanitation DOUBLE,
                water DOUBLE,
                road DOUBLE,
                traffic DOUBLE,
                overall DOUBLE,
                at_risk BOOLEAN,
                computed_at TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                prediction_id VARCHAR,
                issue_id VARCHAR,
                ward_id VARCHAR,
                flood_risk DOUBLE,
                road_risk DOUBLE,
                volume_forecast VARCHAR,
                computed_at TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id VARCHAR,
                issue_id VARCHAR,
                ward_id VARCHAR,
                assigned_department VARCHAR,
                priority VARCHAR,
                status VARCHAR,
                due_date TIMESTAMP,
                created_at TIMESTAMP
            )
        """)

    async def query_historical_issues(
        self, ward_id: str, issue_type: str, days: int
    ) -> list[dict[str, Any]]:
        """Query historical issues from DuckDB (replaces BigQuery)."""
        import asyncio
        loop = asyncio.get_event_loop()

        def _sync_query():
            conn = self._ensure_conn()
            result = conn.execute(
                """SELECT * FROM issues
                   WHERE ward_id = ? AND type = ?
                     AND reported_at >= CURRENT_TIMESTAMP - INTERVAL ? DAY""",
                [ward_id, issue_type, days],
            )
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()
            return [dict(zip(columns, row)) for row in rows]

        try:
            return await loop.run_in_executor(None, _sync_query)
        except Exception:
            logger.exception("DuckDB query failed, returning mock data")
            # Return mock data for demo
            now = datetime.now(timezone.utc)
            return [
                {
                    "reported_at": (now - timedelta(days=i * 2)).isoformat(),
                    "type": issue_type,
                    "location": {
                        "lat": 18.5204 + (i * 0.0001),
                        "lng": 73.8567 + (i * 0.0001),
                        "ward_id": ward_id or "w1",
                    },
                }
                for i in range(6)
            ]

    async def write_predictions(self, prediction_record: dict[str, Any]) -> bool:
        """Write a prediction record to DuckDB (replaces BigQuery)."""
        import asyncio
        loop = asyncio.get_event_loop()

        def _sync_write():
            conn = self._ensure_conn()
            record = dict(prediction_record)
            if isinstance(record.get("volume_forecast"), (list, dict)):
                record["volume_forecast"] = json.dumps(record["volume_forecast"])
            conn.execute(
                """INSERT INTO predictions
                   (prediction_id, issue_id, ward_id, flood_risk, road_risk,
                    volume_forecast, computed_at)
                   VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                [
                    record.get("prediction_id", ""),
                    record.get("issue_id", ""),
                    record.get("ward_id", ""),
                    record.get("flood_risk"),
                    record.get("road_risk"),
                    record.get("volume_forecast", ""),
                ],
            )
            return True

        try:
            return await loop.run_in_executor(None, _sync_write)
        except Exception:
            logger.exception("DuckDB write_predictions failed")
            return False

    async def read_community_health_score(self, ward_id: str) -> float | None:
        """Fetch latest health score from DuckDB (replaces BigQuery)."""
        import asyncio
        loop = asyncio.get_event_loop()

        def _sync_read():
            conn = self._ensure_conn()
            result = conn.execute(
                """SELECT overall FROM community_scores
                   WHERE ward_id = ?
                     AND computed_at >= CURRENT_TIMESTAMP - INTERVAL '25' HOUR
                   ORDER BY computed_at DESC LIMIT 1""",
                [ward_id],
            )
            row = result.fetchone()
            return float(row[0]) if row else None

        try:
            score = await loop.run_in_executor(None, _sync_read)
            return score or 85.0
        except Exception:
            logger.exception("DuckDB read failed")
            return 85.0  # Default fallback

    async def get_90d_sub_scores(self, ward_id: str) -> dict[str, float]:
        """Get 90-day sub-scores for health score computation."""
        import asyncio
        loop = asyncio.get_event_loop()

        def _sync():
            conn = self._ensure_conn()
            result = conn.execute(
                """SELECT AVG(infrastructure) as infra, AVG(sanitation) as san,
                          AVG(water) as water, AVG(road) as road, AVG(traffic) as traffic
                   FROM community_scores
                   WHERE ward_id = ?
                     AND score_date >= CURRENT_DATE - INTERVAL '90' DAY""",
                [ward_id],
            )
            row = result.fetchone()
            if row and row[0] is not None:
                return {
                    "roads": float(row[3] or 0),
                    "flooding": float(row[0] or 0),
                    "sanitation": float(row[1] or 0),
                }
            # Mock data for demo
            return {"roads": 75.0, "flooding": 65.0, "sanitation": 80.0}

        return await loop.run_in_executor(None, _sync)

    async def write_ward_health(
        self, ward_id: str, score: float, at_risk: bool
    ) -> None:
        """Write health score to DuckDB."""
        import asyncio
        loop = asyncio.get_event_loop()

        def _sync_write():
            conn = self._ensure_conn()
            conn.execute(
                """INSERT INTO community_scores
                   (ward_id, score_date, overall, at_risk, computed_at)
                   VALUES (?, CURRENT_DATE, ?, ?, CURRENT_TIMESTAMP)""",
                [ward_id, score, at_risk],
            )

        await loop.run_in_executor(None, _sync_write)
