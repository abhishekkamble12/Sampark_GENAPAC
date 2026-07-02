# ──────────────────────────────────────────────────────────────────────────────
# Service Accounts (least-privilege)
# ──────────────────────────────────────────────────────────────────────────────

resource "google_service_account" "api_gateway" {
  account_id   = "sampark-api-gateway"
  display_name = "Sampark API Gateway Service Account"
  project      = var.project_id
}

resource "google_service_account" "langgraph_engine" {
  account_id   = "sampark-langgraph-engine"
  display_name = "Sampark LangGraph Engine Service Account"
  project      = var.project_id
}

resource "google_service_account" "notification_worker" {
  account_id   = "sampark-notification-worker"
  display_name = "Sampark Notification Worker Service Account"
  project      = var.project_id
}

# ──────────────────────────────────────────────────────────────────────────────
# IAM — Secret Manager accessor (all three services need secrets)
# ──────────────────────────────────────────────────────────────────────────────

resource "google_project_iam_member" "api_gateway_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.api_gateway.email}"
}

resource "google_project_iam_member" "langgraph_engine_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.langgraph_engine.email}"
}

resource "google_project_iam_member" "notification_worker_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.notification_worker.email}"
}

# API Gateway — Cloud Logging writer
resource "google_project_iam_member" "api_gateway_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.api_gateway.email}"
}

# LangGraph Engine — Firestore, Pub/Sub, Vertex AI, BigQuery
resource "google_project_iam_member" "langgraph_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.langgraph_engine.email}"
}

resource "google_project_iam_member" "langgraph_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.langgraph_engine.email}"
}

resource "google_project_iam_member" "langgraph_bigquery_user" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.langgraph_engine.email}"
}

resource "google_project_iam_member" "langgraph_aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.langgraph_engine.email}"
}

resource "google_project_iam_member" "langgraph_storage_object_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.langgraph_engine.email}"
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
# Cloud Run v2 — api-gateway
# ──────────────────────────────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "api_gateway" {
  name     = "api-gateway"
  location = var.region
  project  = var.project_id

  ingress = "INGRESS_TRAFFIC_ALL" # Public HTTPS entry point

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
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
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

      # ── Secret Manager-backed env vars ─────────────────────────────────────
      env {
        name = "JWT_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = "sampark-jwt-secret-key"
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
      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = "sampark-redis-url"
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
  ]
}

# Allow unauthenticated public invocation for the API Gateway
resource "google_cloud_run_v2_service_iam_member" "api_gateway_public" {
  project  = google_cloud_run_v2_service.api_gateway.project
  location = google_cloud_run_v2_service.api_gateway.location
  name     = google_cloud_run_v2_service.api_gateway.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ──────────────────────────────────────────────────────────────────────────────
# Cloud Run v2 — langgraph-engine
# ──────────────────────────────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "langgraph_engine" {
  name     = "langgraph-engine"
  location = var.region
  project  = var.project_id

  # Internal traffic only — invoked by api-gateway, not directly from the internet
  ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.langgraph_engine.email

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    # VPC connector for private access to Firestore (VPC-native) and Memorystore
    vpc_access {
      connector = var.vpc_connector
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "${var.artifact_registry}/sampark/langgraph-engine:latest"

      ports {
        container_port = 8081
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        cpu_idle          = false # Keep CPU allocated during request for long LangGraph runs
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

      # ── Secret Manager-backed env vars ─────────────────────────────────────
      env {
        name = "VERTEX_AI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "sampark-vertex-ai-api-key"
            version = "latest"
          }
        }
      }
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
        name = "FIRESTORE_DATABASE_ID"
        value_source {
          secret_key_ref {
            secret  = "sampark-firestore-database-id"
            version = "latest"
          }
        }
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8081
        }
        initial_delay_seconds = 15
        period_seconds        = 30
        failure_threshold     = 3
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8081
        }
        initial_delay_seconds = 10
        period_seconds        = 5
        failure_threshold     = 15
      }
    }
  }

  depends_on = [
    google_project_iam_member.langgraph_engine_secret_accessor,
    google_project_iam_member.langgraph_firestore_user,
    google_project_iam_member.langgraph_pubsub_publisher,
    google_project_iam_member.langgraph_bigquery_user,
    google_project_iam_member.langgraph_aiplatform_user,
  ]
}

# Allow api-gateway service account to invoke langgraph-engine
resource "google_cloud_run_v2_service_iam_member" "langgraph_engine_api_gateway_invoker" {
  project  = google_cloud_run_v2_service.langgraph_engine.project
  location = google_cloud_run_v2_service.langgraph_engine.location
  name     = google_cloud_run_v2_service.langgraph_engine.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.api_gateway.email}"
}

# ──────────────────────────────────────────────────────────────────────────────
# Cloud Run v2 — notification-worker
# ──────────────────────────────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "notification_worker" {
  name     = "notification-worker"
  location = var.region
  project  = var.project_id

  # Receives Pub/Sub push deliveries — internal + load balancer
  ingress = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    service_account = google_service_account.notification_worker.email

    scaling {
      min_instance_count = 0 # Scale to zero when no messages
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

      # ── Non-secret env vars ────────────────────────────────────────────────
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "REGION"
        value = var.region
      }

      # ── Secret Manager-backed env vars ─────────────────────────────────────
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

# ──────────────────────────────────────────────────────────────────────────────
# Pub/Sub push subscription — notification-worker trigger
#
# Pub/Sub pushes task-created and task-escalated messages to the worker's
# /pubsub/push endpoint. The Pub/Sub service account must be allowed to invoke
# the Cloud Run service.
# ──────────────────────────────────────────────────────────────────────────────

# Grant the Cloud Run invoker role to the Pub/Sub service account so it can
# deliver push messages to notification-worker
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
  message_retention_duration = "86400s" # 24 hours

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

# ──────────────────────────────────────────────────────────────────────────────
# Outputs
# ──────────────────────────────────────────────────────────────────────────────

output "api_gateway_url" {
  description = "Public URL of the API Gateway Cloud Run service"
  value       = google_cloud_run_v2_service.api_gateway.uri
}

output "langgraph_engine_url" {
  description = "Internal URL of the LangGraph Engine Cloud Run service"
  value       = google_cloud_run_v2_service.langgraph_engine.uri
}

output "notification_worker_url" {
  description = "URL of the Notification Worker Cloud Run service"
  value       = google_cloud_run_v2_service.notification_worker.uri
}

output "api_gateway_service_account" {
  description = "Service account email for the API Gateway"
  value       = google_service_account.api_gateway.email
}

output "langgraph_engine_service_account" {
  description = "Service account email for the LangGraph Engine"
  value       = google_service_account.langgraph_engine.email
}

output "notification_worker_service_account" {
  description = "Service account email for the Notification Worker"
  value       = google_service_account.notification_worker.email
}
