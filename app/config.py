import os


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


# Module-level singleton — all other modules import this
settings = Settings()
