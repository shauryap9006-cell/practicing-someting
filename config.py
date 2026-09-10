"""RailTwin-X Central Configuration Engine.

Zero hardcoding: all database paths, API keys, thresholds, corridor parameters,
ML hyperparameters, and operational constants are dynamically resolved from
environment variables or .env files with sensible defaults.
"""

from __future__ import annotations

from pathlib import Path
from typing import List
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Application settings with environment variable override support."""

    model_config = SettingsConfigDict(
        env_prefix="RAILTWIN_",
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 1. Environment & Paths
    APP_NAME: str = Field(
        default="RailTwin-X", validation_alias=AliasChoices("RAILTWIN_APP_NAME", "APP_NAME")
    )
    ENV: str = Field(
        default="development",
        validation_alias=AliasChoices(
            "RAILTWIN_ENV", "ENV", "RAILTWIN_ENVIRONMENT", "ENVIRONMENT"
        ),
        description="'development', 'production', 'test'",
    )
    JWT_SECRET_KEY: str = Field(
        default="",
        validation_alias=AliasChoices(
            "RAILTWIN_JWT_SECRET_KEY", "JWT_SECRET_KEY", "RAILTWIN_SECRET_KEY"
        ),
        description="Signing key for access and refresh tokens; required and >=32 characters in production",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=120)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=30)
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = BASE_DIR / "data" / "railtwin.db"
    SCHEMA_PATH: Path = BASE_DIR / "data" / "schema.sql"
    SEEDS_DIR: Path = BASE_DIR / "data" / "seeds"
    ARTIFACTS_DIR: Path = BASE_DIR / "ml" / "artifacts"
    REPLAY_DIR: Path = BASE_DIR / "engine" / "replay"

    # 2. Time & Clock
    TIMEZONE_NAME: str = "Asia/Kolkata"
    TIMEZONE_OFFSET_HOURS: float = 5.5
    DEFAULT_CLOCK_MODE: str = Field(
        default="live",
        validation_alias=AliasChoices("RAILTWIN_DEFAULT_CLOCK_MODE", "DEFAULT_CLOCK_MODE"),
        description="'live' or 'replay'",
    )
    SIM_CLOCK_START: str = Field(
        default="auto", validation_alias=AliasChoices("RAILTWIN_SIM_CLOCK_START", "SIM_CLOCK_START")
    )
    SIM_CLOCK_ACCEL: float = Field(
        default=1.0, validation_alias=AliasChoices("RAILTWIN_SIM_CLOCK_ACCEL", "SIM_CLOCK_ACCEL")
    )
    DEMO_ALLOW_CLOCK_CONTROL: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "RAILTWIN_DEMO_ALLOW_CLOCK_CONTROL", "DEMO_ALLOW_CLOCK_CONTROL"
        ),
    )
    ALLOW_SYNTHETIC_FALLBACK: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "RAILTWIN_ALLOW_SYNTHETIC_FALLBACK", "ALLOW_SYNTHETIC_FALLBACK"
        ),
        description="Permit mock replay only for an explicitly configured demo/replay environment",
    )
    # 3. External API Settings
    RAPIDAPI_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("RAILTWIN_RAPIDAPI_KEY", "RAPIDAPI_KEY"),
        description="RapidAPI Indian Railways API Key (optional)",
    )
    RAPIDAPI_HOST: str = "indianrailways.p.rapidapi.com"
    RAPIDAPI_BASE_URL: str = "https://indianrailways.p.rapidapi.com"
    OPENMETEO_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPENMETEO_ARCHIVE_URL: str = "https://archive-api.open-meteo.com/v1/archive"
    REQUEST_TIMEOUT_SECONDS: float = 10.0
    POLITE_SCRAPE_DELAY_SECONDS: float = 2.0
    ENABLE_WEB_SCRAPING: bool = Field(
        default=False,
        validation_alias=AliasChoices("RAILTWIN_ENABLE_WEB_SCRAPING", "ENABLE_WEB_SCRAPING"),
        description="Whether to attempt live web scraping when RapidAPI keys are absent",
    )

    # 4. Data Quality Gates & Thresholds
    MAX_SANITY_DELAY_MINUTES: int = Field(default=600, description="Delays > 600m are quarantined")
    MIN_SANITY_DELAY_MINUTES: int = Field(
        default=-120, description="Early arrivals > 120m quarantined"
    )
    STALE_EVENT_THRESHOLD_HOURS: int = 24
    DEAD_TRAIN_CONSECUTIVE_DAYS: int = 3

    # 5. Weather Thresholds (Dynamic Fog/Rain Rules)
    FOG_MAX_TEMP_CELSIUS: float = 18.0
    FOG_MIN_HUMIDITY_PERCENT: float = 85.0
    HEAVY_RAIN_THRESHOLD_MM: float = 25.0

    # 6. Machine Learning Hyperparameters
    ML_TRAIN_DAYS: int = 21  # 3 weeks train
    ML_TEST_DAYS: int = 7  # 1 week test
    DIRECT_MODEL_MAX_HOPS: int = 3  # <=3 hops use Direct model, >3 use Delta model
    QUANTILE_ALPHAS: List[float] = [0.1, 0.5, 0.9]
    CONFORMAL_MISCOVERAGE_ALPHA: float = 0.2  # 1 - alpha = 80% coverage target
    LGBM_NUM_LEAVES: int = 63
    LGBM_LEARNING_RATE: float = 0.05
    LGBM_N_ESTIMATORS: int = 600
    LGBM_MIN_CHILD_SAMPLES: int = 40
    MIN_TEST_SAMPLES: int = Field(
        default=1000,
        validation_alias=AliasChoices("RAILTWIN_MIN_TEST_SAMPLES", "MIN_TEST_SAMPLES"),
        description="Minimum test samples required for a CV fold to be included in aggregate metrics",
    )

    # 7. Operations & Platform Optimization (M4)
    MAX_REOPT_PASSES: int = 50
    PLATFORM_SWAP_PENALTY_WEIGHT: float = 1.5
    CREW_DUTY_HOURS_CAP: float = 10.0
    CREW_DUTY_WARNING_BUFFER_MINUTES: int = 60
    DEFAULT_PLATFORM_DWELL_BUFFER_MINUTES: int = 15

    # Assumed Policy Constants (Deterministic fallback rules when live sensor/crew feeds are absent)
    DEFAULT_NOMINAL_CREW_DUTY_MINUTES: int = Field(
        default=360,
        description="Assumed policy: 6-hour standard baseline scheduled crew shift before actual delay",
    )
    DEFAULT_PLATFORM_HASH_SEED: int = Field(
        default=42,
        description="Assumed policy: deterministic fallback platform assignment hash seed",
    )

    # 8. API & Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_POLL_INTERVAL_SECONDS: int = 5
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    # 9. WhatsApp Gateway & Notification Dispatcher (OpenWA + SMS Fallback)
    OPENWA_URL: str = Field(
        default="http://localhost:2785",
        validation_alias=AliasChoices("RAILTWIN_OPENWA_URL", "OPENWA_URL"),
        description="OpenWA Gateway Base URL",
    )
    OPENWA_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("RAILTWIN_OPENWA_API_KEY", "OPENWA_API_KEY"),
        description="OpenWA Session API Key",
    )
    OPENWA_SESSION_ID: str = Field(
        default="railtwin-alerts",
        validation_alias=AliasChoices("RAILTWIN_OPENWA_SESSION_ID", "OPENWA_SESSION_ID"),
        description="OpenWA Session ID",
    )
    OPENWA_WEBHOOK_SECRET: str = Field(
        default="",
        validation_alias=AliasChoices("RAILTWIN_OPENWA_WEBHOOK_SECRET", "OPENWA_WEBHOOK_SECRET"),
        description="HMAC-SHA256 Secret for Inbound Webhook",
    )
    PUBLIC_URL: str = Field(
        default="http://localhost:8000",
        validation_alias=AliasChoices("RAILTWIN_PUBLIC_URL", "PUBLIC_URL"),
        description="Public Base URL for Webhooks (e.g. ngrok / LAN IP)",
    )
    WHATSAPP_PROVIDER: str = Field(
        default="openwa",
        validation_alias=AliasChoices("RAILTWIN_WHATSAPP_PROVIDER", "WHATSAPP_PROVIDER"),
        description="'openwa' or 'meta'",
    )
    SMS_PROVIDER: str = Field(
        default="mock",
        validation_alias=AliasChoices("RAILTWIN_SMS_PROVIDER", "SMS_PROVIDER"),
        description="'msg91', 'fast2sms', or 'mock'",
    )
    SMS_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("RAILTWIN_SMS_API_KEY", "SMS_API_KEY"),
        description="SMS Fallback API Key",
    )
    SMS_SENDER_ID: str = Field(
        default="RLTWIN",
        validation_alias=AliasChoices("RAILTWIN_SMS_SENDER_ID", "SMS_SENDER_ID"),
        description="Sender Header ID for SMS",
    )
    NOTIFICATION_RATE_LIMIT_MINUTES: float = Field(
        default=2.0,
        validation_alias=AliasChoices(
            "RAILTWIN_NOTIFICATION_RATE_LIMIT_MINUTES", "NOTIFICATION_RATE_LIMIT_MINUTES"
        ),
        description="Max 1 alert per N minutes per staff member",
    )
    NOTIFY_DEMO_MODE: bool = Field(
        default=False,
        validation_alias=AliasChoices("RAILTWIN_NOTIFY_DEMO_MODE", "NOTIFY_DEMO_MODE"),
        description="When true, redirects all outbound alert phone numbers to a fixed sandbox whitelist (demo/hackathon use only). Must be false so real staff receive alerts.",
    )

    # 10. Pipeline 07: Live Position Tracking, Context & Real Delay Attribution
    LIVE_SOURCE_MODE: str = Field(
        default="auto",
        validation_alias=AliasChoices("RAILTWIN_LIVE_SOURCE_MODE", "LIVE_SOURCE_MODE"),
        description="'auto', 'live', 'replay', or 'simulated'",
    )
    LIVE_TRACKER_INTERVAL_SECONDS: int = Field(
        default=1,
        validation_alias=AliasChoices(
            "RAILTWIN_LIVE_TRACKER_INTERVAL_SECONDS", "LIVE_TRACKER_INTERVAL_SECONDS"
        ),
        description="Master live tracker tick interval in seconds",
    )
    LIVE_STATION_POLL_SECONDS: int = Field(
        default=30,
        validation_alias=AliasChoices(
            "RAILTWIN_LIVE_STATION_POLL_SECONDS", "LIVE_STATION_POLL_SECONDS"
        ),
        description="Interval for station-board batch status polls in seconds",
    )
    LIVE_POLL_TPM_BUDGET: int = Field(
        default=100,
        validation_alias=AliasChoices("RAILTWIN_LIVE_POLL_TPM_BUDGET", "LIVE_POLL_TPM_BUDGET"),
        description="Max individual RapidAPI train status queries per minute",
    )
    ATTRIBUTION_DELTA_MIN: float = Field(
        default=5.0,
        validation_alias=AliasChoices("RAILTWIN_ATTRIBUTION_DELTA_MIN", "ATTRIBUTION_DELTA_MIN"),
        description="Minimum delay jump in minutes to trigger live attribution",
    )
    ATTRIBUTION_UNEXPLAINED_TOLERANCE_MIN: float = Field(
        default=0.5,
        validation_alias=AliasChoices(
            "RAILTWIN_ATTRIBUTION_UNEXPLAINED_TOLERANCE_MIN",
            "ATTRIBUTION_UNEXPLAINED_TOLERANCE_MIN",
        ),
        description="Residual tolerance before logging UNEXPLAINED cause",
    )
    WEATHER_CACHE_MINUTES: int = Field(
        default=15,
        validation_alias=AliasChoices("RAILTWIN_WEATHER_CACHE_MINUTES", "WEATHER_CACHE_MINUTES"),
        description="TTL for station weather telemetry cache in minutes",
    )
    POSITION_CACHE_TTL_SECONDS: int = Field(
        default=60,
        validation_alias=AliasChoices(
            "RAILTWIN_POSITION_CACHE_TTL_SECONDS", "POSITION_CACHE_TTL_SECONDS"
        ),
        description="TTL for in-memory train position cache in seconds",
    )
    LIVE_SSE_PULSE_SECONDS: int = Field(
        default=5,
        validation_alias=AliasChoices("RAILTWIN_LIVE_SSE_PULSE_SECONDS", "LIVE_SSE_PULSE_SECONDS"),
        description="Server-Sent Events streaming interval for live positions in seconds",
    )
    CONTEXT_CACHE_TTL_SECONDS: int = Field(
        default=10,
        validation_alias=AliasChoices(
            "RAILTWIN_CONTEXT_CACHE_TTL_SECONDS", "CONTEXT_CACHE_TTL_SECONDS"
        ),
        description="TTL for enriched operational train context cache in seconds",
    )
    CONFIDENCE_TAU_SECONDS: float = Field(
        default=120.0,
        validation_alias=AliasChoices("RAILTWIN_CONFIDENCE_TAU_SECONDS", "CONFIDENCE_TAU_SECONDS"),
        description="Characteristic decay tau in seconds for confidence exp(-Δt/τ)",
    )
    DEAD_RECKON_MIN_CONFIDENCE: float = Field(
        default=0.3,
        validation_alias=AliasChoices(
            "RAILTWIN_DEAD_RECKON_MIN_CONFIDENCE", "DEAD_RECKON_MIN_CONFIDENCE"
        ),
        description="Confidence threshold below which position is marked STALE",
    )

    # 11. Shared-stream and request-safety limits
    MAX_SSE_CONNECTIONS: int = Field(default=250, ge=1, le=10000)
    SSE_MAX_DURATION_SECONDS: int = Field(default=1800, ge=30, le=86400)

    # 12. API Rate Limiting (Token Bucket)
    RATE_LIMIT_RPM: int = Field(
        default=1200,
        validation_alias=AliasChoices("RAILTWIN_RATE_LIMIT_RPM", "RATE_LIMIT_RPM"),
        description="Requests per minute per IP for the token-bucket rate limiter",
    )
    RATE_LIMIT_BURST: int = Field(
        default=300,
        validation_alias=AliasChoices("RAILTWIN_RATE_LIMIT_BURST", "RATE_LIMIT_BURST"),
        description="Max burst tokens above the steady RATE_LIMIT_RPM rate",
    )
    TRUST_PROXY_HEADERS: bool = Field(
        default=False,
        description="Only honour X-Forwarded-For for rate limiting when the API sits behind a trusted reverse proxy",
    )
    RESPONSE_CACHE_TTL_SECONDS: float = Field(default=5.0, ge=0.0, le=300.0)
    IDEMPOTENCY_TTL_SECONDS: int = Field(default=24 * 60 * 60, ge=60, le=7 * 24 * 60 * 60)
    WEBHOOK_MAX_TIMESTAMP_AGE_SECONDS: int = Field(default=300, ge=30, le=3600)
    MIN_PASSWORD_LENGTH: int = Field(default=12, ge=8, le=128)

    # 13. Domain defaults (previously scattered as literals across routers/services)
    DEFAULT_STATION_CODE: str = Field(
        default="NDLS",
        description="Fallback station scope used when a caller does not specify one",
    )
    DEFAULT_JUNCTION_CODE: str = Field(
        default="CNB",
        description="Default interchange junction for cascade/ripple analysis and health smoke tests",
    )
    DEMO_DEFAULT_TRAIN_NO: str = Field(
        default="12301", description="Default corridor train for demo surfaces and smoke tests"
    )
    DEMO_DEFAULT_DESTINATION_CODE: str = Field(
        default="LKO", description="Default destination for demo time-machine"
    )
    DEMO_DEFAULT_RUN_DATE: str = Field(
        default="",
        description="Fallback run date (YYYY-MM-DD) for demo replays; empty resolves to the latest recorded run",
    )
    DELAY_ON_TIME_MAX_MIN: int = Field(
        default=15, ge=0, description="Delays up to this are shown green"
    )
    DELAY_MODERATE_MAX_MIN: int = Field(
        default=60, ge=0, description="Delays up to this are shown amber, beyond is red"
    )
    HORIZON_1H_MAX_KM: float = Field(default=90.0, gt=0)
    HORIZON_3H_MAX_KM: float = Field(default=250.0, gt=0)
    OFFICIAL_RUNRATE_RECOVERY_KM_PER_MIN: float = Field(
        default=30.0,
        gt=0,
        description="Official timetable slack recovery assumption: 1 minute recovered per N km",
    )
    SECTION_CAPACITY_HEADWAY_KM: float = Field(
        default=10.0,
        gt=0,
        description="Planning headway used to derive block-section train capacity (length_km / headway_km)",
    )
    TSR_MIN_SPEED_KMPH: int = Field(
        default=20, ge=5, le=60, description="Floor for demo-injected caution orders"
    )
    RAKE_MIN_TURNAROUND_BUFFER_MIN: int = Field(
        default=90, ge=0, description="Minimum rake cleaning/inspection buffer"
    )
    DEFAULT_RAKE_TURNAROUND_MIN: int = Field(default=240, ge=0)
    DEFAULT_MIN_CONNECTION_TIME_MIN: int = Field(default=15, ge=1, le=120)
    TELEMETRY_STALE_SECONDS: int = Field(
        default=900, ge=30, description="Snapshot age after which the feed is flagged STALE"
    )
    NOTIFY_DEMO_CONTROLLER_PHONE: str = Field(
        default="",
        description="Sandbox phone for controller-role alerts when NOTIFY_DEMO_MODE is on (never hardcode real numbers)",
    )
    NOTIFY_DEMO_FIELD_PHONE: str = Field(
        default="",
        description="Sandbox phone for field-staff alerts when NOTIFY_DEMO_MODE is on",
    )

    # 13. Data Privacy & Retention (DPDP Act 2023)
    PII_RETENTION_DAYS: int = Field(
        default=90,
        ge=1,
        validation_alias=AliasChoices("RAILTWIN_PII_RETENTION_DAYS", "PII_RETENTION_DAYS"),
        description="Number of days to retain identifiable personal data (delay certificates, notification logs, passenger records) under DPDP Act 2023 before redaction/purge",
    )

    @model_validator(mode="after")
    def validate_runtime_safety(self) -> "Settings":
        """Reject deployment configurations that would silently weaken security."""
        environment = self.ENV.strip().lower()
        if self.NOTIFY_DEMO_MODE and not (
            self.NOTIFY_DEMO_CONTROLLER_PHONE.strip() and self.NOTIFY_DEMO_FIELD_PHONE.strip()
        ):
            raise ValueError(
                "RAILTWIN_NOTIFY_DEMO_MODE requires RAILTWIN_NOTIFY_DEMO_CONTROLLER_PHONE and RAILTWIN_NOTIFY_DEMO_FIELD_PHONE"
            )
        if self.DELAY_MODERATE_MAX_MIN < self.DELAY_ON_TIME_MAX_MIN:
            raise ValueError(
                "RAILTWIN_DELAY_MODERATE_MAX_MIN must be >= RAILTWIN_DELAY_ON_TIME_MAX_MIN"
            )
        if self.HORIZON_3H_MAX_KM <= self.HORIZON_1H_MAX_KM:
            raise ValueError(
                "RAILTWIN_HORIZON_3H_MAX_KM must be greater than RAILTWIN_HORIZON_1H_MAX_KM"
            )
        if environment == "production":
            if self.DEMO_ALLOW_CLOCK_CONTROL:
                raise ValueError("RAILTWIN_DEMO_ALLOW_CLOCK_CONTROL must be false in production")
            if self.ALLOW_SYNTHETIC_FALLBACK:
                raise ValueError("RAILTWIN_ALLOW_SYNTHETIC_FALLBACK must be false in production")
            secret = self.JWT_SECRET_KEY.strip()
            insecure_patterns = (
                "insecure",
                "development",
                "changeme",
                "secret",
                "default",
                "placeholder",
                "dummy",
                "example",
                "replace-with",
            )
            if len(secret) < 32 or any(p in secret.lower() for p in insecure_patterns):
                raise ValueError(
                    "RAILTWIN_JWT_SECRET_KEY must be a cryptographically secure secret of at least 32 characters, and cannot contain insecure placeholder words in production"
                )
            if self.DEFAULT_CLOCK_MODE != "live":
                raise ValueError("RAILTWIN_DEFAULT_CLOCK_MODE must be 'live' in production")
            if not self.CORS_ORIGINS or any(
                "localhost" in origin or "127.0.0.1" in origin for origin in self.CORS_ORIGINS
            ):
                raise ValueError(
                    "Production CORS_ORIGINS must contain only explicitly configured public origins"
                )
            public_url = self.PUBLIC_URL.strip()
            parsed_public_url = urlparse(public_url)
            if parsed_public_url.scheme not in {"http", "https"} or not parsed_public_url.netloc:
                raise ValueError("RAILTWIN_PUBLIC_URL must be a valid http(s) URL in production")
            if "localhost" in public_url.lower() or "127.0.0.1" in public_url:
                raise ValueError(
                    "RAILTWIN_PUBLIC_URL must not contain localhost or 127.0.0.1 in production"
                )
            if self.WHATSAPP_PROVIDER == "openwa" and not self.OPENWA_WEBHOOK_SECRET.strip():
                raise ValueError(
                    "RAILTWIN_OPENWA_WEBHOOK_SECRET is required when the OpenWA webhook is enabled"
                )
            if self.NOTIFY_DEMO_MODE:
                raise ValueError(
                    "RAILTWIN_NOTIFY_DEMO_MODE must be false in production so real staff receive alerts"
                )
        return self


# Singleton instance
settings = Settings()

if __name__ == "__main__":
    print("=== RailTwin-X Dynamic Settings ===")
    print(f"App Name: {settings.APP_NAME}")
    print(f"Database Path: {settings.DB_PATH}")
    print(f"Quantile Alphas: {settings.QUANTILE_ALPHAS}")
    print(f"Conformal Coverage Target: {(1 - settings.CONFORMAL_MISCOVERAGE_ALPHA) * 100:.0f}%")
    print(f"Quality Gate Max Delay: {settings.MAX_SANITY_DELAY_MINUTES} min")
    print(f"Crew Duty Cap: {settings.CREW_DUTY_HOURS_CAP} hours")
    print(f"Live Tracker Interval: {settings.LIVE_TRACKER_INTERVAL_SECONDS}s")
    print(f"Live Station Poll: {settings.LIVE_STATION_POLL_SECONDS}s")
    print(f"Attribution Delta Min: {settings.ATTRIBUTION_DELTA_MIN}m")
