from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "vt-clickfix-vmray"
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://app:app@db:5432/app"

    vt_api_key: str = ""
    vt_poll_interval_seconds: int = 300
    vt_enabled: bool = False

    vmray_url: str = ""
    vmray_api_key: str = ""
    vmray_poll_interval_seconds: int = 60
    vmray_enabled: bool = False

    pipeline_autostart: bool = False


settings = Settings()
