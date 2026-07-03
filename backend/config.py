import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_MODE: str = os.getenv("APP_MODE", "local")
    
    JWT_SECRET: str = os.getenv("JWT_SECRET", "mock_secret_key")
    JWT_ALGORITHM: str = "HS256"
    
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "sampark-demo")
    FIRESTORE_DATABASE: str = os.getenv("FIRESTORE_DATABASE", "(default)")
    BIGQUERY_DATASET: str = os.getenv("BIGQUERY_DATASET", "sampark_analytics")
    
    MAPS_API_KEY: str = os.getenv("MAPS_API_KEY", "")
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")
    
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", os.getenv("VERTEX_AI_API_KEY", ""))
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", os.getenv("MAPS_API_KEY", ""))
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", os.getenv("WEATHER_API_KEY", ""))
    
    PUBSUB_TOPIC_TASK_CREATED: str = os.getenv("PUBSUB_TOPIC_TASK_CREATED", "task-created")
    
    DEMO_ADMIN_USERNAME: str = os.getenv("DEMO_ADMIN_USERNAME", "admin")
    DEMO_ADMIN_PASSWORD: str = os.getenv("DEMO_ADMIN_PASSWORD", "password")
    DEMO_LEADER_USERNAME: str = os.getenv("DEMO_LEADER_USERNAME", "leader_w1")
    DEMO_LEADER_PASSWORD: str = os.getenv("DEMO_LEADER_PASSWORD", "password")
    
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "*")
    
    class Config:
        env_file = ".env"

settings = Settings()
