from pydantic_settings import BaseSettings
from pydantic import field_validator
import os

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgres://postgres:password@localhost:5432/anime_db")
    claude_api_key: str = os.getenv("CLAUDE_API_KEY", "")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    serpapi_key: str = os.getenv("SERPAPI_KEY", "")
    model_name: str = os.getenv("MODEL_NAME", "anthropic/claude-3.5-sonnet")
    port: int = int(os.getenv("PORT", 8000))
    environment: str = os.getenv("ENVIRONMENT", "development")

    @field_validator("model_name")
    @classmethod
    def strip_openrouter_prefix(cls, v):
        return v.replace("openrouter/", "") if v else v

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
