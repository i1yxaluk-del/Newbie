from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Domik Alina"
    APP_ENV: str = "dev"
    APP_SECRET: str = "change-me"
    CORS_ORIGINS: str = "http://localhost:5173"

    ADMIN_EMAIL: str = "admin@domik.local"
    ADMIN_PASSWORD: str = "ChangeMe2026!"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True
    NOTIFY_EMAIL_TO: str = ""

    TG_BOT_TOKEN: str = ""
    TG_CHAT_ID: str = ""

    DATABASE_URL: str = "sqlite:///./data/domik.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
