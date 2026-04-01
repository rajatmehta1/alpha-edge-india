"""Alpha Edge — Configuration via Pydantic Settings.
All environment variables loaded from .env with type validation and defaults."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # LLM
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TEMPERATURE: float = 0.3
    GROQ_MAX_TOKENS: int = 1024

    # Data Sources
    TWITTER_BEARER_TOKEN: str = ""

    # Report
    REPORT_OUTPUT_DIR: str = "./output"
    GENERATE_PDF: bool = False

    # Trading Config
    TRADING_CAPITAL: int = 2400000
    MAX_RISK_PER_TRADE_PCT: float = 1.0
    MAX_DAILY_LOSS_PCT: float = 2.5
    MAX_CONCURRENT_POSITIONS: int = 3

    # Schedule
    REPORT_TIME: str = "07:00"
    MARKET_OPEN_TIME: str = "09:15"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Database
    DB_PATH: str = "./storage/alpha_edge.db"

    # Timeouts
    COLLECTOR_TIMEOUT: int = 30
    AGENT_TIMEOUT: int = 60

    # Groq rate limit management
    AGENT_DELAY_SECONDS: float = 3.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
