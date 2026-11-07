"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized, typed application settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+asyncpg://careeruser:careerpass@db:5432/careerdb"
    redis_url: str = "redis://redis:6379/0"

    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:3000,http://localhost"

    google_sheets_enabled: bool = True
    anthropic_api_key: str = ""

    # --- LLM provider chain (free tier) ---
    gemini_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    llm_primary_model: str = "gemini-flash-lite-latest"
    llm_fallback_model: str = "gemini-2.5-flash-lite"

    # --- BYOK encryption (Fernet) ---
    encryption_key: str = ""

    # --- Crustdata ---
    crustdata_api_key: str = ""

    # --- Agent runtime ---
    agent_max_steps: int = 8
    agent_credit_budget: float = 50.0
    agent_dry_run_default: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so env parsing happens once."""
    return Settings()
