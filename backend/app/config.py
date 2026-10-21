from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgres://postgres:password@localhost:5432/anime_db")
    claude_api_key: str = os.getenv("CLAUDE_API_KEY", "")
    port: int = int(os.getenv("PORT", 8000))
    environment: str = os.getenv("ENVIRONMENT", "development")

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
