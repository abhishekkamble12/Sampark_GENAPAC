# ──────────────────────────────────────────────────────────────────────────────
# Service Accounts (least-privilege)
# ──────────────────────────────────────────────────────────────────────────────

resource "google_service_account" "api_gateway" {
  account_id   = "sampark-api-gateway"
  display_name = "Sampark API Gateway Service Account (ADK)"
  project      = var.project_id
}

resource "google_service_account" "notification_worker" {
  account_id   = "sampark-notification-worker"
  display_name = "Sampark Notification Worker Service Account"
  project      = var.project_id
}

# ──────────────────────────────────────────────────────────────────────────────
# IAM — Secret Manager accessor
# ──────────────────────────────────────────────────────────────────────────────

resource "google_project_iam_member" "api_gateway_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.api_gateway.email}"
}

resource "google_project_iam_member" "notification_worker_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.notification_worker.email}"
}

# API Gateway — Cloud Logging writer + Firestore + BigQuery + Vertex AI + Pub/Sub + Storage
resource "google_project_iam_member" "api_gateway_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.api_gateway.email}"
}

resource "google_project_iam_member" "api_gateway_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.api_gateway.email}"
}

resource "google_project_iam_member" "api_gateway_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.api_gateway.email}"
}

resource "google_project_iam_member" "api_gateway_bigquery_user" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.api_gateway.email}"
}

resource "google_project_iam_member" "api_gateway_aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.api_gateway.email}"
}

resource "google_project_iam_member" "api_gateway_storage_object_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.api_gateway.email}"
}

# Notification Worker — Firestore, Pub/Sub subscriber, Cloud Logging
resource "google_project_iam_member" "notification_worker_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.notification_worker.email}"
}

resource "google_project_iam_member" "notification_worker_pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.notification_worker.email}"
}

resource "google_project_iam_member" "notification_worker_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.notification_worker.email}"
}

# ──────────────────────────────────────────────────────────────────────────────
# Cloud Run v2 — api-gateway (ADK pipeline runs inline, no separate engine)
# ──────────────────────────────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "api_gateway" {
  name     = "api-gateway"
  location = var.region
  project  = var.project_id

  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.api_gateway.email

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    containers {
      image = "${var.artifact_registry}/sampark/api-gateway:latest"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
        cpu_idle          = false
        startup_cpu_boost = true
      }

      # ── Non-secret env vars ────────────────────────────────────────────────
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "REGION"
        value = var.region
      }
      env {
        name  = "APP_MODE"
        value = "production"
      }
      env {
        name  = "RAG_CORPUS_ID"
        value = var.rag_corpus_id
      }

      # ── Secret Manager-backed env vars ─────────────────────────────────────
      env {
        name = "GOOGLE_MAPS_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "sampark-google-maps-api-key"
            version = "latest"
          }
        }
      }
      env {
        name = "WEATHER_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "sampark-weather-api-key"
            version = "latest"
          }
        }
      }
      env {
        name = "FIREBASE_CREDENTIALS"
        value_source {
          secret_key_ref {
            secret  = "sampark-firebase-credentials"
            version = "latest"
          }
        }
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 10
        period_seconds        = 30
        failure_threshold     = 3
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 10
      }
    }
  }

  depends_on = [
    google_project_iam_member.api_gateway_secret_accessor,
    google_project_iam_member.api_gateway_log_writer,
    google_project_iam_member.api_gateway_firestore_user,
    google_project_iam_member.api_gateway_pubsub_publisher,
    google_project_iam_member.api_gateway_bigquery_user,
    google_project_iam_member.api_gateway_aiplatform_user,
  ]
}

# Allow unauthenticated public invocation
resource "google_cloud_run_v2_service_iam_member" "api_gateway_public" {
  project  = google_cloud_run_v2_service.api_gateway.project
  location = google_cloud_run_v2_service.api_gateway.location
  name     = google_cloud_run_v2_service.api_gateway.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ──────────────────────────────────────────────────────────────────────────────
# Cloud Run v2 — notification-worker
# ──────────────────────────────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "notification_worker" {
  name     = "notification-worker"
  location = var.region
  project  = var.project_id

  ingress = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    service_account = google_service_account.notification_worker.email

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    containers {
      image = "${var.artifact_registry}/sampark/notification-worker:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "REGION"
        value = var.region
      }

      env {
        name = "TWILIO_ACCOUNT_SID"
        value_source {
          secret_key_ref {
            secret  = "sampark-twilio-account-sid"
            version = "latest"
          }
        }
      }
      env {
        name = "TWILIO_AUTH_TOKEN"
        value_source {
          secret_key_ref {
            secret  = "sampark-twilio-auth-token"
            version = "latest"
          }
        }
      }
      env {
        name = "SENDGRID_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "sampark-sendgrid-api-key"
            version = "latest"
          }
        }
      }
      env {
        name = "FCM_SERVER_KEY"
        value_source {
          secret_key_ref {
            secret  = "sampark-fcm-server-key"
            version = "latest"
          }
        }
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 10
        period_seconds        = 30
        failure_threshold     = 3
      }
    }
  }

  depends_on = [
    google_project_iam_member.notification_worker_secret_accessor,
    google_project_iam_member.notification_worker_firestore_user,
    google_project_iam_member.notification_worker_pubsub_subscriber,
  ]
}

# Pub/Sub push subscription for notification-worker
resource "google_cloud_run_v2_service_iam_member" "notification_worker_pubsub_invoker" {
  project  = google_cloud_run_v2_service.notification_worker.project
  location = google_cloud_run_v2_service.notification_worker.location
  name     = google_cloud_run_v2_service.notification_worker.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

data "google_project" "project" {
  project_id = var.project_id
}

resource "google_pubsub_subscription" "task_created_push" {
  name    = "task-created-notification-worker-push"
  topic   = "projects/${var.project_id}/topics/task-created"
  project = var.project_id

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.notification_worker.uri}/pubsub/push"
    oidc_token {
      service_account_email = google_service_account.notification_worker.email
      audience              = google_cloud_run_v2_service.notification_worker.uri
    }
  }

  ack_deadline_seconds       = 60
  message_retention_duration = "86400s"
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  depends_on = [google_cloud_run_v2_service.notification_worker]
}

resource "google_pubsub_subscription" "task_escalated_push" {
  name    = "task-escalated-notification-worker-push"
  topic   = "projects/${var.project_id}/topics/task-escalated"
  project = var.project_id

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.notification_worker.uri}/pubsub/push"
    oidc_token {
      service_account_email = google_service_account.notification_worker.email
      audience              = google_cloud_run_v2_service.notification_worker.uri
    }
  }

  ack_deadline_seconds       = 60
  message_retention_duration = "86400s"
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  depends_on = [google_cloud_run_v2_service.notification_worker]
}

# ── Outputs ──────────────────────────────────────────────────────────

output "api_gateway_url" {
  description = "Public URL of the API Gateway Cloud Run service"
  value       = google_cloud_run_v2_service.api_gateway.uri
}

output "notification_worker_url" {
  description = "URL of the Notification Worker Cloud Run service"
  value       = google_cloud_run_v2_service.notification_worker.uri
}

output "api_gateway_service_account" {
  description = "Service account email for the API Gateway"
  value       = google_service_account.api_gateway.email
}

output "notification_worker_service_account" {
  description = "Service account email for the Notification Worker"
  value       = google_service_account.notification_worker.email
}
