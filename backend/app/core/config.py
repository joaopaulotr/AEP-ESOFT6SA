from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "app_db"
    openai_api_key: str = ""
    llm_provider: Literal["openai", "fake"] = "openai"
    llm_model: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"


settings = Settings()
