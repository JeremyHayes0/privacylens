from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized application configuration, loaded from environment
    variables (or a local .env file in development).

    Using pydantic-settings means every config value is typed and
    validated at process startup: a missing DATABASE_URL or
    JWT_SECRET_KEY fails immediately and loudly when the app boots,
    instead of surfacing later as a confusing runtime error deep inside
    a request handler.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Database ---
    DATABASE_URL: str

    # --- Queue (scan worker) ---
    # SECURITY/OPS: no credentials are embedded by default because
    # local development points at an unauthenticated local Redis; a
    # deployed environment should use a URL with credentials/TLS
    # (rediss://) supplied via the environment, never hardcoded here.
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- JWT / Auth ---
    # SECURITY: JWT_SECRET_KEY signs every access token. It must be a
    # long, random, secret value in any non-local environment, is never
    # hardcoded, and is never committed to source control (see
    # .env.example, which ships only a placeholder). Rotating this value
    # immediately invalidates every previously issued token.
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    # --- App metadata ---
    PROJECT_NAME: str = "PrivacyLens"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"


# A single, module-level Settings instance. Importing `settings` from
# this module elsewhere in the app is the only sanctioned way to read
# configuration — nothing else should call os.environ directly.
settings = Settings()
