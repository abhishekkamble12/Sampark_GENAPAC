"""
backend/config.py — Sampark AI Platform Configuration (FREE Stack)

All Google Cloud dependencies removed. Uses only free services:
- Google AI Studio (Gemini API)
- SQLite (local database)
- DuckDB (analytics)
- FAISS (vector search)
- python-dotenv (.env)
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_MODE: str = os.getenv("APP_MODE", "local")

    # JWT Authentication
    JWT_SECRET: str = os.getenv("JWT_SECRET", "sampark_dev_secret_key")
    JWT_ALGORITHM: str = "HS256"

    # === FREE Google AI Studio (replaces Vertex AI) ===
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # === FREE Gemini Embeddings (replaces Vertex AI Embeddings) ===
    GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")

    # === Third-party APIs (free tiers) ===
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")

    # === Local Database Paths (replaces Firestore + BigQuery) ===
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "data/sampark.db")
    DUCKDB_PATH: str = os.getenv("DUCKDB_PATH", "data/sampark_analytics.duckdb")
    FAISS_INDEX_PATH: str = os.getenv("FAISS_INDEX_PATH", "data/policy_index.faiss")
    VECTOR_METADATA_PATH: str = os.getenv("VECTOR_METADATA_PATH", "data/policy_metadata.json")

    # === Pub/Sub replacement (in-memory async queue) ===
    USE_ASYNC_QUEUE: bool = os.getenv("USE_ASYNC_QUEUE", "true").lower() == "true"

    # === Demo Credentials ===
    DEMO_ADMIN_USERNAME: str = os.getenv("DEMO_ADMIN_USERNAME", "admin")
    DEMO_ADMIN_PASSWORD: str = os.getenv("DEMO_ADMIN_PASSWORD", "password")
    DEMO_LEADER_USERNAME: str = os.getenv("DEMO_LEADER_USERNAME", "leader_w1")
    DEMO_LEADER_PASSWORD: str = os.getenv("DEMO_LEADER_PASSWORD", "password")

    # === CORS ===
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "*")

    class Config:
        env_file = ".env"


settings = Settings()
