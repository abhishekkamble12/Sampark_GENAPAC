-- sql/sampark_dashboard_view.sql
-- 16.1 Create BigQuery SQL view `sampark_dashboard_view`
-- 16.2 Expose required columns without additional joins.

CREATE OR REPLACE VIEW sampark_dashboard_view AS
WITH daily_issues AS (
    SELECT 
        ward_id,
        DATE(reported_at) as event_date,
        COUNT(issue_id) as complaint_volume,
        COUNTIF(status = 'resolved') as resolved_count,
        COUNTIF(status != 'resolved' AND severity = 'Critical') as open_critical_count
    FROM `sampark_analytics.issues`
    GROUP BY ward_id, event_date
),
daily_scores AS (
    SELECT 
        ward_id,
        DATE(computed_at) as event_date,
        AVG(overall) as avg_health_score
    FROM `sampark_analytics.community_scores`
    GROUP BY ward_id, event_date
),
daily_predictions AS (
    SELECT
        ward_id,
        DATE(computed_at) as event_date,
        MAX(flood_risk) as max_flood_risk,
        MAX(road_risk) as max_road_risk
    FROM `sampark_analytics.predictions`
    GROUP BY ward_id, event_date
),
daily_tasks AS (
    SELECT
        ward_id,
        DATE(created_at) as event_date,
        COUNT(task_id) as total_tasks,
        COUNTIF(status = 'completed') as completed_tasks
    FROM `sampark_analytics.tasks`
    GROUP BY ward_id, event_date
)

SELECT 
    COALESCE(i.ward_id, s.ward_id, p.ward_id, t.ward_id) as ward_id,
    COALESCE(i.event_date, s.event_date, p.event_date, t.event_date) as event_date,
    COALESCE(i.complaint_volume, 0) as complaint_volume,
    COALESCE(s.avg_health_score, 0.0) as avg_health_score,
    COALESCE(p.max_flood_risk, 0.0) as max_flood_risk,
    COALESCE(p.max_road_risk, 0.0) as max_road_risk,
    IF(COALESCE(i.complaint_volume, 0) > 0, COALESCE(i.resolved_count, 0) / COALESCE(i.complaint_volume, 1), 0.0) as resolution_rate,
    COALESCE(i.open_critical_count, 0) as open_critical_count
FROM daily_issues i
FULL OUTER JOIN daily_scores s 
    ON i.ward_id = s.ward_id AND i.event_date = s.event_date
FULL OUTER JOIN daily_predictions p
    ON (i.ward_id = p.ward_id OR s.ward_id = p.ward_id) AND (i.event_date = p.event_date OR s.event_date = p.event_date)
FULL OUTER JOIN daily_tasks t
    ON (COALESCE(i.ward_id, s.ward_id, p.ward_id) = t.ward_id) AND (COALESCE(i.event_date, s.event_date, p.event_date) = t.event_date)
;
