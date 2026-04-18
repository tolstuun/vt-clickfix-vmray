from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "vt-clickfix-vmray"
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://app:app@db:5432/app"


settings = Settings()
