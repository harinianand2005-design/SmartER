from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SmartER API"
    app_env: str = "development"
    debug: bool = False
    database_url: str = "postgresql+psycopg://smarter@localhost:5432/smarter"
    backend_cors_origins: str = "http://localhost:5173"
    jwt_secret_key: str = "development-only-change-this-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    demo_admin_email: str = "admin@example.com"
    demo_admin_password: str = ""
    demo_triage_email: str = "triage@example.com"
    demo_triage_password: str = ""
    demo_health_authority_email: str = "authority@example.com"
    demo_health_authority_password: str = ""
    ml_models_dir: str = "ml/models"
    ml_metadata_path: str = "ml/models/model_metadata.json"
    ml_explainability_dir: str = "ml/explainability/outputs"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()