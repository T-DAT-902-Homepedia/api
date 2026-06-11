"""Configuration de l'API (variables d'environnement)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="ignore" : tolère les variables API_* inconnues (ex. .env hérité).
    model_config = SettingsConfigDict(
        env_prefix="API_", env_file=".env", extra="ignore"
    )

    # Origines autorisées pour CORS (webapp Vite en dev).
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
