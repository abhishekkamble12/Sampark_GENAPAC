# ---------------------------------------------------------------------------
# Pub/Sub topics — Sampark AI Platform
# ---------------------------------------------------------------------------
# task-created        : published by Workflow Agent on task creation
# task-escalated      : published by the Escalation Cloud Function
# health-score-updated: published by Health Score Cloud Function on
#                       at-risk score transitions
# sampark-dead-letter : catch-all dead-letter topic for failed deliveries
# ---------------------------------------------------------------------------

resource "google_pubsub_topic" "task_created" {
  name    = "task-created"
  project = var.project_id

  message_retention_duration = "86400s"
}

resource "google_pubsub_topic" "task_escalated" {
  name    = "task-escalated"
  project = var.project_id

  message_retention_duration = "86400s"
}

resource "google_pubsub_topic" "health_score_updated" {
  name    = "health-score-updated"
  project = var.project_id

  message_retention_duration = "86400s"
}

resource "google_pubsub_topic" "dead_letter" {
  name    = "sampark-dead-letter"
  project = var.project_id

  message_retention_duration = "86400s"
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "pubsub_topic_task_created_id" {
  description = "ID of the task-created Pub/Sub topic"
  value       = google_pubsub_topic.task_created.id
}

output "pubsub_topic_task_escalated_id" {
  description = "ID of the task-escalated Pub/Sub topic"
  value       = google_pubsub_topic.task_escalated.id
}

output "pubsub_topic_health_score_updated_id" {
  description = "ID of the health-score-updated Pub/Sub topic"
  value       = google_pubsub_topic.health_score_updated.id
}

output "pubsub_topic_dead_letter_id" {
  description = "ID of the sampark-dead-letter dead-letter Pub/Sub topic"
  value       = google_pubsub_topic.dead_letter.id
}
