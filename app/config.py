"""Configuration de l'API (variables d'environnement)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="ignore" : tolère les variables API_* inconnues (ex. .env hérité).
    model_config = SettingsConfigDict(
        env_prefix="API_", env_file=".env", extra="ignore"
    )

    # DSN PostgreSQL/PostGIS — REQUIS via l'environnement (API_DATABASE_URL).
    # Aucun secret en dur ici. Ex. dev :
    #   API_DATABASE_URL=postgresql://homepedia:<pwd>@localhost:5432/homepedia
    database_url: str

    # Origines autorisées pour CORS (webapp Vite en dev).
    cors_origins: list[str] = ["http://localhost:5173"]

    # Durée de cache HTTP des réponses choroplèthe (s). La donnée ne change qu'au
    # run du pipeline -> cache long justifié.
    cache_max_age: int = 3600

    # Bornes du pool de connexions asyncpg.
    pool_min_size: int = 1
    pool_max_size: int = 10


settings = Settings()
