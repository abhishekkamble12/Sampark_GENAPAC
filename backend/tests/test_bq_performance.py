"""Performance test for DuckDB analytics (replaces BigQuery View logic - Task 16).

Tests that the DuckDB-based analytical queries complete within SLA
on a dataset of 100k synthetic rows.
"""

import time
import pytest
import duckdb


def setup_in_memory_db():
    conn = duckdb.connect(":memory:")

    # Create tables mirroring the old BQ structure
    conn.execute("""
        CREATE TABLE issues (
            issue_id VARCHAR, ward_id VARCHAR, created_at TIMESTAMP,
            status VARCHAR, priority VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE community_scores (
            ward_id VARCHAR, computed_at TIMESTAMP, health_score DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE predictions (
            ward_id VARCHAR, predicted_at TIMESTAMP, risk_type VARCHAR, risk_score DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE tasks (
            task_id VARCHAR, ward_id VARCHAR, created_at TIMESTAMP, status VARCHAR
        )
    """)

    # Seed 100,000 synthetic rows across tables
    issues_data = [(f"i{i}", f"w{i%10}", time.strftime("%Y-%m-%d %H:%M:%S"),
                    "open", "Critical") for i in range(25000)]
    scores_data = [(f"w{i%10}", time.strftime("%Y-%m-%d %H:%M:%S"), 85.0)
                   for i in range(25000)]
    preds_data = [(f"w{i%10}", time.strftime("%Y-%m-%d %H:%M:%S"), "flooding", 0.9)
                  for i in range(25000)]
    tasks_data = [(f"t{i}", f"w{i%10}", time.strftime("%Y-%m-%d %H:%M:%S"), "completed")
                  for i in range(25000)]

    conn.executemany("INSERT INTO issues VALUES (?, ?, ?, ?, ?)", issues_data)
    conn.executemany("INSERT INTO community_scores VALUES (?, ?, ?)", scores_data)
    conn.executemany("INSERT INTO predictions VALUES (?, ?, ?, ?)", preds_data)
    conn.executemany("INSERT INTO tasks VALUES (?, ?, ?, ?)", tasks_data)

    return conn


def test_duckdb_analytics_performance():
    conn = setup_in_memory_db()

    # DuckDB translation of the dashboard aggregator query
    query = """
        WITH daily_issues AS (
            SELECT ward_id, CAST(created_at AS DATE) as event_date,
                   COUNT(issue_id) as complaint_volume,
                   SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved_count,
                   SUM(CASE WHEN status != 'resolved' AND priority = 'Critical' THEN 1 ELSE 0 END) as open_critical_count
            FROM issues GROUP BY ward_id, event_date
        ),
        daily_scores AS (
            SELECT ward_id, CAST(computed_at AS DATE) as event_date,
                   AVG(health_score) as avg_health_score
            FROM community_scores GROUP BY ward_id, event_date
        ),
        daily_predictions AS (
            SELECT ward_id, CAST(predicted_at AS DATE) as event_date,
                   MAX(CASE WHEN risk_type = 'flooding' THEN risk_score ELSE 0 END) as max_flood_risk,
                   MAX(CASE WHEN risk_type = 'road' THEN risk_score ELSE 0 END) as max_road_risk
            FROM predictions GROUP BY ward_id, event_date
        ),
        daily_tasks AS (
            SELECT ward_id, CAST(created_at AS DATE) as event_date,
                   COUNT(task_id) as total_tasks,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks
            FROM tasks GROUP BY ward_id, event_date
        )
        SELECT i.ward_id, i.event_date, i.complaint_volume,
               COALESCE(s.avg_health_score, 0.0) as avg_health_score,
               COALESCE(p.max_flood_risk, 0.0) as max_flood_risk,
               COALESCE(p.max_road_risk, 0.0) as max_road_risk,
               i.open_critical_count
        FROM daily_issues i
        LEFT JOIN daily_scores s ON i.ward_id = s.ward_id AND i.event_date = s.event_date
        LEFT JOIN daily_predictions p ON i.ward_id = p.ward_id AND i.event_date = p.event_date
        LEFT JOIN daily_tasks t ON i.ward_id = t.ward_id AND i.event_date = t.event_date
    """

    start_time = time.perf_counter()
    result = conn.execute(query)
    rows = result.fetchall()
    duration = time.perf_counter() - start_time

    # Assert query completes in < 3s on 100k row equivalent dataset
    assert duration < 3.0, f"DuckDB query took {duration:.2f}s (exceeded 3s SLA)"
    assert len(rows) > 0
