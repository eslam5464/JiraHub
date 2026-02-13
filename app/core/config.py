from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Admin
    admin_email: str = Field(description="Email of the admin user (auto-approved on register)")

    # Email domain restriction
    allowed_email_domain: str = Field(
        default="dar.com",
        description="Only emails ending with @{domain} can register",
    )

    # Security
    encryption_key: str = Field(description="Fernet key for encrypting Jira API tokens")
    secret_key: str = Field(min_length=32, description="Secret key for session token signing")

    # Session
    session_expiry_hours: int = Field(default=72, description="Session expiry in hours")

    # Redis
    redis_host: str
    redis_port: int
    redis_db: int
    redis_user: str
    redis_pass: str

    # Network
    proxy_url: str | None = Field(
        default=None,
        description="HTTP/HTTPS proxy URL (e.g., http://proxy.example.com:8080)",
    )

    # Database
    db_path: str = Field(default="./data/jira_app.db", description="Path to SQLite database file")

    # App
    app_name: str = Field(default="Jira Team Dashboard")
    debug: bool = Field(default=False)

    @computed_field
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_user}:{self.redis_pass}@{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @computed_field
    @property
    def db_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.db_path}"

    @computed_field
    @property
    def db_directory(self) -> Path:
        return Path(self.db_path).parent


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
