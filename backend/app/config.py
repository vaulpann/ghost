from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://ghost:ghost@localhost:5432/ghost"

    # OpenAI
    openai_api_key: str = ""

    # GitHub
    github_token: str = ""

    # Alerting
    slack_webhook_url: str = ""

    # Polling intervals (seconds)
    poll_interval_critical: int = 60
    poll_interval_high: int = 120
    poll_interval_medium: int = 300
    poll_interval_low: int = 900

    # LLM models
    triage_model: str = "gpt-4o-mini"
    deep_analysis_model: str = "gpt-4o"
    synthesis_model: str = "gpt-4o"

    # Frontend URL (for alert links)
    frontend_url: str = "http://localhost:3000"

    # Admin API key (for write endpoints and webhooks)
    admin_api_key: str = ""

    # Audit Worker (GCE VM)
    audit_worker_url: str = ""
    audit_worker_api_key: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
