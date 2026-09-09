"""
Centralized application configuration, loaded from environment variables / .env.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: str = "groq"  
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    database_url: str = "sqlite:///./cars24_ops.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()