# ─────────────────────────────────────────────────────────────────────────────
# BigQuery — sampark_analytics dataset
# ─────────────────────────────────────────────────────────────────────────────

resource "google_bigquery_dataset" "sampark_analytics" {
  project     = var.project_id
  dataset_id  = "sampark_analytics"
  location    = var.region
  description = "Sampark AI Platform analytics dataset"

  labels = {
    env     = "production"
    product = "sampark"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Table: issues
# ─────────────────────────────────────────────────────────────────────────────

resource "google_bigquery_table" "issues" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.sampark_analytics.dataset_id
  table_id   = "issues"

  description = "Raw issue reports submitted by citizens"

  deletion_protection = false

  schema = jsonencode([
    {
      name = "issue_id"
      type = "STRING"
      mode = "REQUIRED"
      description = "Unique issue identifier"
    },
    {
      name = "type"
      type = "STRING"
      mode = "NULLABLE"
      description = "Issue category (road, sanitation, water, electricity, flood, traffic, health, other)"
    },
    {
      name = "ward_id"
      type = "STRING"
      mode = "NULLABLE"
      description = "Ward identifier where the issue was reported"
    },
    {
      name = "lat"
      type = "FLOAT64"
      mode = "NULLABLE"
      description = "Latitude of the reported issue"
    },
    {
      name = "lng"
      type = "FLOAT64"
      mode = "NULLABLE"
      description = "Longitude of the reported issue"
    },
    {
      name = "severity"
      type = "STRING"
      mode = "NULLABLE"
      description = "Severity level: Critical, High, Medium, Low"
    },
    {
      name = "status"
      type = "STRING"
      mode = "NULLABLE"
      description = "Current status: open, in_progress, resolved"
    },
    {
      name = "reported_at"
      type = "TIMESTAMP"
      mode = "NULLABLE"
      description = "Timestamp when the issue was reported"
    },
    {
      name = "resolved_at"
      type = "TIMESTAMP"
      mode = "NULLABLE"
      description = "Timestamp when the issue was resolved (null if unresolved)"
    }
  ])
}

# ─────────────────────────────────────────────────────────────────────────────
# Table: community_scores
# ─────────────────────────────────────────────────────────────────────────────

resource "google_bigquery_table" "community_scores" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.sampark_analytics.dataset_id
  table_id   = "community_scores"

  description = "Daily community health scores computed per ward"

  deletion_protection = false

  schema = jsonencode([
    {
      name = "ward_id"
      type = "STRING"
      mode = "NULLABLE"
      description = "Ward identifier"
    },
    {
      name = "score_date"
      type = "DATE"
      mode = "NULLABLE"
      description = "Date for which the scores were computed"
    },
    {
      name = "infrastructure"
      type = "FLOAT64"
      mode = "NULLABLE"
      description = "Infrastructure sub-score (0–100)"
    },
    {
      name = "sanitation"
      type = "FLOAT64"
      mode = "NULLABLE"
      description = "Sanitation sub-score (0–100)"
    },
    {
      name = "water"
      type = "FLOAT64"
      mode = "NULLABLE"
      description = "Water supply sub-score (0–100)"
    },
    {
      name = "road"
      type = "FLOAT64"
      mode = "NULLABLE"
      description = "Road condition sub-score (0–100)"
    },
    {
      name = "traffic"
      type = "FLOAT64"
      mode = "NULLABLE"
      description = "Traffic management sub-score (0–100)"
    },
    {
      name = "overall"
      type = "FLOAT64"
      mode = "NULLABLE"
      description = "Weighted composite health score (0–100)"
    },
    {
      name = "at_risk"
      type = "BOOL"
      mode = "NULLABLE"
      description = "True when overall score < 60"
    },
    {
      name = "computed_at"
      type = "TIMESTAMP"
      mode = "NULLABLE"
      description = "Timestamp when this score row was computed"
    }
  ])
}

# ─────────────────────────────────────────────────────────────────────────────
# Table: predictions
# ─────────────────────────────────────────────────────────────────────────────

resource "google_bigquery_table" "predictions" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.sampark_analytics.dataset_id
  table_id   = "predictions"

  description = "ML risk predictions and volume forecasts per issue / ward"

  deletion_protection = false

  schema = jsonencode([
    {
      name = "prediction_id"
      type = "STRING"
      mode = "REQUIRED"
      description = "Unique prediction identifier"
    },
    {
      name = "issue_id"
      type = "STRING"
      mode = "NULLABLE"
      description = "Foreign key referencing the source issue"
    },
    {
      name = "ward_id"
      type = "STRING"
      mode = "NULLABLE"
      description = "Ward for which the prediction was generated"
    },
    {
      name = "flood_risk"
      type = "FLOAT64"
      mode = "NULLABLE"
      description = "Flood risk score in [0.0, 1.0]"
    },
    {
      name = "road_risk"
      type = "FLOAT64"
      mode = "NULLABLE"
      description = "Road degradation risk score in [0.0, 1.0]"
    },
    {
      name = "volume_forecast"
      type = "STRING"
      mode = "NULLABLE"
      description = "JSON-serialised 7-day complaint volume forecast array"
    },
    {
      name = "computed_at"
      type = "TIMESTAMP"
      mode = "NULLABLE"
      description = "Timestamp when this prediction was computed"
    }
  ])
}

# ─────────────────────────────────────────────────────────────────────────────
# Outputs
# ─────────────────────────────────────────────────────────────────────────────

output "bigquery_dataset_id" {
  description = "The ID of the sampark_analytics BigQuery dataset"
  value       = google_bigquery_dataset.sampark_analytics.dataset_id
}

output "bigquery_issues_table_id" {
  description = "Fully-qualified ID of the issues table"
  value       = google_bigquery_table.issues.id
}

output "bigquery_community_scores_table_id" {
  description = "Fully-qualified ID of the community_scores table"
  value       = google_bigquery_table.community_scores.id
}

output "bigquery_predictions_table_id" {
  description = "Fully-qualified ID of the predictions table"
  value       = google_bigquery_table.predictions.id
}
