from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Its own local .env, not the original project's root .env — this app is
    # meant to run fully independently, on its own database and port.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://lenderfinder:lenderfinder@localhost:5433/lender_finder"
    cors_origins: str = "http://localhost:3000"
    firebase_service_account_path: str = "firebase-service-account.json"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
