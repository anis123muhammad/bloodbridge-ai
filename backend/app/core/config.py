"""Application settings, read from environment variables (or a local .env file)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "BloodBridge AI API"
    environment: str = "development"
    # Used to interpret phrases like "by 6pm" or "tonight" in free-text requests
    app_timezone: str = "Asia/Karachi"

    # Database
    database_url: str = "postgresql+psycopg://bloodbridge:bloodbridge@localhost:5432/bloodbridge"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # CORS: comma-separated list of allowed frontend origins
    cors_origins: str = "http://localhost:3000"

    # Vultr Serverless Inference (optional). If the key is empty the agents use
    # their deterministic fallbacks and the app still works end to end.
    vultr_inference_api_key: str = ""
    vultr_inference_base_url: str = "https://api.vultrinference.com/v1"
    vultr_inference_model: str = ""
    llm_timeout_seconds: float = 20.0

    # Workflow rules (operational, NOT medical)
    matching_radius_steps_km: str = "25,50,100"
    max_candidates: int = 8
    min_days_between_donations_demo: int = 90
    invitation_timeout_minutes: int = 30
    follow_up_interval_seconds: int = 60
    enable_background_follow_up: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def radius_steps(self) -> list[float]:
        return [float(x) for x in self.matching_radius_steps_km.split(",") if x.strip()]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.vultr_inference_api_key and self.vultr_inference_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()
