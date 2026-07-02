variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud region for resource deployment"
  type        = string
  default     = "asia-south1"
}

variable "artifact_registry" {
  description = "Artifact Registry host (e.g. asia-south1-docker.pkg.dev/my-project/my-repo)"
  type        = string
}

variable "vpc_connector" {
  description = "Fully-qualified VPC Serverless Access connector name for private VPC access"
  type        = string
  default     = ""
}

variable "notification_worker_pubsub_audience" {
  description = "Pub/Sub push subscription audience URL for notification-worker (Cloud Run service URL)"
  type        = string
  default     = ""
}
