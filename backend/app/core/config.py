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
    smtp_starttls: bool = True   # port 465 uses implicit TLS instead
    app_url: str = "http://localhost:5173"   # used in email links
    google_client_id: str = ""
    reset_token_minutes: int = 30
    reset_max_per_hour: int = 3


settings = Settings()
