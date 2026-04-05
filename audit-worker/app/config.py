from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    worker_api_key: str = ""
    audit_dir: str = "/var/ghost-audits"
    max_concurrent_audits: int = 1
    max_queue_depth: int = 10
    cost_cap_usd: float = 15.0
    codex_discovery_model: str = "o3"
    codex_validation_model: str = "o3"
    codex_timeout_secs: int = 900  # 15 min per pass
    callback_timeout_secs: int = 30

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
