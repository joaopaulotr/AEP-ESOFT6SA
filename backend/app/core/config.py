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
    frontend_url: str = "http://localhost:5173"
    # Preços de referência (USD) para ESTIMAR o custo por entrevista (gpt-4o-mini, whisper-1, tts).
    # São estimativas configuráveis, não a fatura da OpenAI.
    price_llm_input_per_1m: float = 0.15
    price_llm_output_per_1m: float = 0.60
    price_stt_per_minute: float = 0.006
    price_tts_per_1m_chars: float = 15.0

    class Config:
        env_file = ".env"


settings = Settings()
