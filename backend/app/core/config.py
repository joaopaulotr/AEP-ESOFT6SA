from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "app_db"
    openai_api_key: str = ""
    llm_provider: Literal["openai", "fake"] = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 20.0
    max_audio_bytes: int = 25 * 1024 * 1024
    max_upload_bytes: int = 2 * 1024 * 1024

    class Config:
        env_file = ".env"


settings = Settings()
