from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "LLV Assistant"
    app_env: str = "development"
    app_debug: bool = True
    secret_key: str = "dev-secret-key-change-in-production"
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Base de datos
    db_host: str = "db"
    db_port: int = 3306
    db_name: str = "llv_assistant"
    db_user: str = "llv_user"
    db_password: str = "llv_password"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+mysqldb://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?charset=utf8mb4"
        )

    # Gemini AI
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

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
