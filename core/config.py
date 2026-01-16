from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_days: int = 30
    frontend_base_url: str = "http://localhost"
    mail_mode: str = "console"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    admin_api_key: str
    enable_dev_endpoints: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
