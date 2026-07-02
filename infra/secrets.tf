# ──────────────────────────────────────────────────────────────────────────────
# Google Secret Manager — Secret Containers
#
# These resources create the secret *containers* only.
# Secret *values* must be populated manually (via gcloud, Console, or CI/CD)
# before any Cloud Run service that references them can be deployed.
#
# To add a value:
#   gcloud secrets versions add <SECRET_ID> --data-file=<path-to-file> \
#     --project=<PROJECT_ID>
# ──────────────────────────────────────────────────────────────────────────────

# ── api-gateway secrets ────────────────────────────────────────────────────────

resource "google_secret_manager_secret" "jwt_secret_key" {
  secret_id = "sampark-jwt-secret-key"
  project   = var.project_id

  labels = {
    app       = "sampark"
    service   = "api-gateway"
    secret_type = "auth"
  }

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "firebase_credentials" {
  secret_id = "sampark-firebase-credentials"
  project   = var.project_id

  labels = {
    app         = "sampark"
    service     = "api-gateway"
    secret_type = "credentials"
  }

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "redis_url" {
  secret_id = "sampark-redis-url"
  project   = var.project_id

  labels = {
    app         = "sampark"
    service     = "api-gateway"
    secret_type = "connection"
  }

  replication {
    auto {}
  }
}

# ── langgraph-engine secrets ───────────────────────────────────────────────────

resource "google_secret_manager_secret" "vertex_ai_api_key" {
  secret_id = "sampark-vertex-ai-api-key"
  project   = var.project_id

  labels = {
    app         = "sampark"
    service     = "langgraph-engine"
    secret_type = "api-key"
  }

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "google_maps_api_key" {
  secret_id = "sampark-google-maps-api-key"
  project   = var.project_id

  labels = {
    app         = "sampark"
    service     = "langgraph-engine"
    secret_type = "api-key"
  }

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "weather_api_key" {
  secret_id = "sampark-weather-api-key"
  project   = var.project_id

  labels = {
    app         = "sampark"
    service     = "langgraph-engine"
    secret_type = "api-key"
  }

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "firestore_database_id" {
  secret_id = "sampark-firestore-database-id"
  project   = var.project_id

  labels = {
    app         = "sampark"
    service     = "langgraph-engine"
    secret_type = "config"
  }

  replication {
    auto {}
  }
}

# ── notification-worker secrets ────────────────────────────────────────────────

resource "google_secret_manager_secret" "twilio_account_sid" {
  secret_id = "sampark-twilio-account-sid"
  project   = var.project_id

  labels = {
    app         = "sampark"
    service     = "notification-worker"
    secret_type = "credentials"
  }

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "twilio_auth_token" {
  secret_id = "sampark-twilio-auth-token"
  project   = var.project_id

  labels = {
    app         = "sampark"
    service     = "notification-worker"
    secret_type = "credentials"
  }

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "sendgrid_api_key" {
  secret_id = "sampark-sendgrid-api-key"
  project   = var.project_id

  labels = {
    app         = "sampark"
    service     = "notification-worker"
    secret_type = "api-key"
  }

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "fcm_server_key" {
  secret_id = "sampark-fcm-server-key"
  project   = var.project_id

  labels = {
    app         = "sampark"
    service     = "notification-worker"
    secret_type = "credentials"
  }

  replication {
    auto {}
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# Outputs — Secret resource IDs for reference in other modules
# ──────────────────────────────────────────────────────────────────────────────

output "secret_jwt_secret_key_id" {
  description = "Resource ID of the JWT secret key secret"
  value       = google_secret_manager_secret.jwt_secret_key.id
}

output "secret_firebase_credentials_id" {
  description = "Resource ID of the Firebase credentials secret"
  value       = google_secret_manager_secret.firebase_credentials.id
}

output "secret_redis_url_id" {
  description = "Resource ID of the Redis URL secret"
  value       = google_secret_manager_secret.redis_url.id
}

output "secret_vertex_ai_api_key_id" {
  description = "Resource ID of the Vertex AI API key secret"
  value       = google_secret_manager_secret.vertex_ai_api_key.id
}

output "secret_google_maps_api_key_id" {
  description = "Resource ID of the Google Maps API key secret"
  value       = google_secret_manager_secret.google_maps_api_key.id
}

output "secret_weather_api_key_id" {
  description = "Resource ID of the Weather API key secret"
  value       = google_secret_manager_secret.weather_api_key.id
}

output "secret_firestore_database_id_id" {
  description = "Resource ID of the Firestore database ID secret"
  value       = google_secret_manager_secret.firestore_database_id.id
}

output "secret_twilio_account_sid_id" {
  description = "Resource ID of the Twilio Account SID secret"
  value       = google_secret_manager_secret.twilio_account_sid.id
}

output "secret_twilio_auth_token_id" {
  description = "Resource ID of the Twilio auth token secret"
  value       = google_secret_manager_secret.twilio_auth_token.id
}

output "secret_sendgrid_api_key_id" {
  description = "Resource ID of the SendGrid API key secret"
  value       = google_secret_manager_secret.sendgrid_api_key.id
}

output "secret_fcm_server_key_id" {
  description = "Resource ID of the FCM server key secret"
  value       = google_secret_manager_secret.fcm_server_key.id
}
