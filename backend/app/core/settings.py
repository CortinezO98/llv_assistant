from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "LLV Assistant"
    app_env: str = "development"
    app_debug: bool = True
    secret_key: str = "dev-secret-key-change-in-production"
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: Any) -> list[str]:
        """Acepta JSON array o cadena separada por comas."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # Base de datos
    db_host: str = "127.0.0.1"
    db_port: int = 3307
    db_name: str = "llv_assistant"
    db_user: str = "root"
    db_password: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"mysql+mysqldb://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?charset=utf8mb4"
        )

    # Gemini AI
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-preview-04-17"

    # WhatsApp
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""
    webhook_verify_token: str = "llv_webhook_verify_2024"

    # Plan y alertas
    plan_monthly_limit: int = 1500
    alert_email_80_percent: bool = True
    alert_email_100_percent: bool = True
    admin_alert_email: str = ""

    # SMTP
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "LLV Assistant Sistema"

    # Pagos
    default_payment_method: str = "zelle"

    # Vagaro (fase 2)
    vagaro_api_key: str = ""
    vagaro_merchant_id: str = ""

    # Workers
    conversation_worker_interval: int = 5
    conversation_worker_batch: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
