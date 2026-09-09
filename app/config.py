from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: str = "groq"  
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    database_url: str = "sqlite:///./cars24_ops.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()