import os
import secrets
from dataclasses import dataclass, field

_DEV_SECRET = secrets.token_urlsafe(48)  # regenerated per process in dev; sessions reset on restart


def _bool(name, default):
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes")


@dataclass
class Settings:
    env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./seo_dev.db"))
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", ""))
    jwt_issuer: str = "ai-seo-platform"
    jwt_audience: str = "ai-seo-platform-web"
    access_minutes: int = field(default_factory=lambda: int(os.getenv("ACCESS_TOKEN_MINUTES", "30")))
    refresh_days: int = field(default_factory=lambda: int(os.getenv("REFRESH_TOKEN_DAYS", "7")))
    cookie_secure: bool = field(default_factory=lambda: _bool("COOKIE_SECURE", False))
    cors_origins: list = field(default_factory=lambda: [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()])
    ai_provider: str = field(default_factory=lambda: os.getenv("AI_PROVIDER", "mock"))  # mock|openai|anthropic
    ai_model: str = field(default_factory=lambda: os.getenv("AI_MODEL", ""))
    ai_base_url: str = field(default_factory=lambda: os.getenv("AI_BASE_URL", "https://api.openai.com/v1"))
    ai_api_key: str = field(default_factory=lambda: os.getenv("AI_API_KEY", ""))
    ai_timeout: float = field(default_factory=lambda: float(os.getenv("AI_TIMEOUT_SECONDS", "60")))
    ai_max_retries: int = field(default_factory=lambda: int(os.getenv("AI_MAX_RETRIES", "2")))
    ai_max_output_tokens: int = field(default_factory=lambda: int(os.getenv("AI_MAX_OUTPUT_TOKENS", "4000")))
    ai_daily_limit: int = field(default_factory=lambda: int(os.getenv("AI_DAILY_LIMIT_PER_USER", "100")))
    rate_limit_enabled: bool = field(default_factory=lambda: _bool("RATE_LIMIT_ENABLED", True))
    ai_rate_per_min: int = field(default_factory=lambda: int(os.getenv("AI_RATE_PER_MINUTE", "10")))
    auth_rate_per_min: int = field(default_factory=lambda: int(os.getenv("AUTH_RATE_PER_MINUTE", "10")))
    fetch_timeout: float = 8.0
    fetch_max_bytes: int = 1_000_000

    def __post_init__(self):
        if not self.secret_key:
            if self.env == "production":
                raise RuntimeError("SECRET_KEY must be set in production")
            self.secret_key = _DEV_SECRET


def get_settings() -> Settings:
    return Settings()
