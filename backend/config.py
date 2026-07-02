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
    
    PUBSUB_TOPIC_TASK_CREATED: str = os.getenv("PUBSUB_TOPIC_TASK_CREATED", "task-created")
    
    class Config:
        env_file = ".env"

settings = Settings()
