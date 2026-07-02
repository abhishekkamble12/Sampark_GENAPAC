# Sampark Infrastructure

Terraform configurations for the Sampark AI Platform on Google Cloud.

## Resources

- `cloud_run.tf` — Cloud Run services (api-gateway, langgraph-engine, notification-worker)
- `pubsub.tf` — Pub/Sub topics (task-created, task-escalated, health-score-updated)
- `bigquery.tf` — BigQuery dataset `sampark_analytics` with issues, community_scores, predictions tables

## Usage

```bash
terraform init
terraform plan
terraform apply
```
