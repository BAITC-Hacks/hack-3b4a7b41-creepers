from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env", env_file_encoding="utf-8",
        extra="ignore", hide_input_in_errors=True,
    )

    ekt_api_base_url: str = "https://ekt.kz/api"
    ekt_api_username: str = Field(default="apiuser", repr=False)
    ekt_api_password: SecretStr = Field(default=SecretStr(""), repr=False)
    cors_origins: str = "http://localhost:3000"
    demo_checkout_base_url: str = "http://localhost:3000"
    ekt_timeout_seconds: float = Field(default=10, gt=0, le=60)
    catalog_max_pages: int = Field(default=20, ge=1, le=50)
    catalog_cache_seconds: float = Field(default=60, ge=0, le=3600)
    catalog_search_timeout_seconds: float = Field(default=8, gt=0, le=60)
    session_ttl_seconds: int = Field(default=3600, ge=60)
    max_sessions: int = Field(default=1000, ge=1, le=100000)
    attachment_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    openai_api_key: SecretStr = Field(default=SecretStr(""), repr=False)
    openai_model: str = "gpt-4o-mini"

    @field_validator("ekt_api_base_url", "demo_checkout_base_url")
    @classmethod
    def validate_url(cls, value: str, info):
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise ValueError("Expected an HTTP(S) URL without credentials, query or fragment")
        if info.field_name == "ekt_api_base_url" and parsed.scheme != "https":
            raise ValueError("EKT API requires HTTPS")
        return value.rstrip("/")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
