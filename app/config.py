import os

from dotenv import load_dotenv

load_dotenv()  # loads .env file if present, no-op if missing


class Settings:
    """Application settings loaded from environment variables with documented defaults."""

    def __init__(self):
        self.host: str = os.getenv("HOST", "0.0.0.0")
        self.port: int = int(os.getenv("PORT", "8000"))
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.workers: int = int(os.getenv("WORKERS", "1"))
        self.executor_threads: int = int(os.getenv("EXECUTOR_THREADS", "4"))
        # 0 means no timeout
        self.model_timeout: int = int(os.getenv("MODEL_TIMEOUT", "30"))
        # Rate limit for the analyse endpoint, e.g. "10/minute"
        self.rate_limit: str = os.getenv("RATE_LIMIT", "10/minute")
        # Number of retry attempts on transient RuntimeError (0 = no retries)
        self.model_retries: int = int(os.getenv("MODEL_RETRIES", "2"))


# Module-level singleton — all other modules import this
settings = Settings()
