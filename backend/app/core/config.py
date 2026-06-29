from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (set in docker-compose / .env)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- PostgreSQL connection ---
    postgres_user: str = "procurement"
    postgres_password: str = "procurement"
    postgres_db: str = "procurement"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # --- Frontend origin allowed to call this API (CORS) ---
    backend_cors_origins: str = "http://localhost:5173"

    @property
    def database_url(self) -> str:
        """The connection string SQLAlchemy will use to reach Postgres."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Read settings once and cache them, so we don't re-parse env on every call."""
    return Settings()


settings = get_settings()
