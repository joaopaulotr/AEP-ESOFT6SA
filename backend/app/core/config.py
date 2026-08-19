from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "app_db"

    class Config:
        env_file = ".env"


settings = Settings()
