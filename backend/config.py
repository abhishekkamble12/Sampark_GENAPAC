import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────────────────
    APP_MODE: str = "local"

    # ── Google Cloud ───────────────────────────────────────────────────
    GCP_PROJECT_ID: str = "sampark-demo"
    GCP_LOCATION: str = "us-central1"
    FIRESTORE_DATABASE: str = "(default)"
    BIGQUERY_DATASET: str = "sampark_analytics"

    # ── Google ADK ─────────────────────────────────────────────────────
    GOOGLE_API_KEY: str = ""
    GOOGLE_CLOUD_PROJECT: str = "sampark-demo"
    GOOGLE_CLOUD_LOCATION: str = "us-central1"
    GOOGLE_GENAI_USE_ENTERPRISE: bool = False

    # ── Vertex AI RAG Engine ───────────────────────────────────────────
    RAG_CORPUS_ID: str = ""
    RAG_CORPUS_NAME: str = ""

    # ── External APIs ──────────────────────────────────────────────────
    GOOGLE_MAPS_API_KEY: str = ""
    OPENWEATHER_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # ── Pub/Sub ────────────────────────────────────────────────────────
    PUBSUB_TOPIC_TASK_CREATED: str = "task-created"

    # ── Demo Users ─────────────────────────────────────────────────────
    DEMO_ADMIN_USERNAME: str = "admin"
    DEMO_ADMIN_PASSWORD: str = "password"
    DEMO_LEADER_USERNAME: str = "leader_w1"
    DEMO_LEADER_PASSWORD: str = "password"

    # ── Logging ────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── CORS ───────────────────────────────────────────────────────────
    CORS_ALLOWED_ORIGINS: str = "*"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
