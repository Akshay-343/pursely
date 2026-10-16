from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://money:money@localhost:5432/moneytracker"
    secret_key: str = "dev-secret-change-me"
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    cors_origins: str = "http://localhost:5173"
    run_scheduler: bool = True
    upload_dir: str = "./uploads"
    max_upload_mb: int = 5
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""


settings = Settings()
