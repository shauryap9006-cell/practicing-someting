"""RailTwin-X Central Configuration Engine.

Zero hardcoding: all database paths, API keys, thresholds, corridor parameters,
ML hyperparameters, and operational constants are dynamically resolved from
environment variables or .env files with sensible defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List
from pydantic import Field, AliasChoices
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
    APP_NAME: str = Field(default="RailTwin-X", validation_alias=AliasChoices("RAILTWIN_APP_NAME", "APP_NAME"))
    ENV: str = Field(default="development", validation_alias=AliasChoices("RAILTWIN_ENV", "ENV"), description="'development', 'production', 'test'")
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = BASE_DIR / "data" / "railtwin.db"
    SCHEMA_PATH: Path = BASE_DIR / "data" / "schema.sql"
    SEEDS_DIR: Path = BASE_DIR / "data" / "seeds"
    ARTIFACTS_DIR: Path = BASE_DIR / "ml" / "artifacts"
    REPLAY_DIR: Path = BASE_DIR / "engine" / "replay"

    # 2. Time & Clock
    TIMEZONE_NAME: str = "Asia/Kolkata"
    TIMEZONE_OFFSET_HOURS: float = 5.5
    DEFAULT_CLOCK_MODE: str = Field(default="live", validation_alias=AliasChoices("RAILTWIN_DEFAULT_CLOCK_MODE", "DEFAULT_CLOCK_MODE"), description="'live' or 'replay'")

    # 3. External API Settings
    RAPIDAPI_KEY: str = Field(default="", validation_alias=AliasChoices("RAILTWIN_RAPIDAPI_KEY", "RAPIDAPI_KEY"), description="RapidAPI Indian Railways API Key (optional)")
    RAPIDAPI_HOST: str = "indianrailways.p.rapidapi.com"
    RAPIDAPI_BASE_URL: str = "https://indianrailways.p.rapidapi.com"
    OPENMETEO_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPENMETEO_ARCHIVE_URL: str = "https://archive-api.open-meteo.com/v1/archive"
    REQUEST_TIMEOUT_SECONDS: float = 10.0
    POLITE_SCRAPE_DELAY_SECONDS: float = 2.0

    # 4. Data Quality Gates & Thresholds
    MAX_SANITY_DELAY_MINUTES: int = Field(default=600, description="Delays > 600m are quarantined")
    MIN_SANITY_DELAY_MINUTES: int = Field(default=-120, description="Early arrivals > 120m quarantined")
    STALE_EVENT_THRESHOLD_HOURS: int = 24
    DEAD_TRAIN_CONSECUTIVE_DAYS: int = 3

    # 5. Weather Thresholds (Dynamic Fog/Rain Rules)
    FOG_MAX_TEMP_CELSIUS: float = 18.0
    FOG_MIN_HUMIDITY_PERCENT: float = 85.0
    HEAVY_RAIN_THRESHOLD_MM: float = 25.0

    # 6. Machine Learning Hyperparameters
    ML_TRAIN_DAYS: int = 21  # 3 weeks train
    ML_TEST_DAYS: int = 7    # 1 week test
    DIRECT_MODEL_MAX_HOPS: int = 3  # <=3 hops use Direct model, >3 use Delta model
    QUANTILE_ALPHAS: List[float] = [0.1, 0.5, 0.9]
    CONFORMAL_MISCOVERAGE_ALPHA: float = 0.2  # 1 - alpha = 80% coverage target
    LGBM_NUM_LEAVES: int = 63
    LGBM_LEARNING_RATE: float = 0.05
    LGBM_N_ESTIMATORS: int = 600
    LGBM_MIN_CHILD_SAMPLES: int = 40

    # 7. Operations & Platform Optimization (M4)
    MAX_REOPT_PASSES: int = 50
    PLATFORM_SWAP_PENALTY_WEIGHT: float = 1.5
    CREW_DUTY_HOURS_CAP: float = 10.0
    CREW_DUTY_WARNING_BUFFER_MINUTES: int = 60
    DEFAULT_PLATFORM_DWELL_BUFFER_MINUTES: int = 15

    # Assumed Policy Constants (Deterministic fallback rules when live sensor/crew feeds are absent)
    DEFAULT_NOMINAL_CREW_DUTY_MINUTES: int = Field(
        default=360,
        description="Assumed policy: 6-hour standard baseline scheduled crew shift before actual delay"
    )
    DEFAULT_PLATFORM_HASH_SEED: int = Field(
        default=42,
        description="Assumed policy: deterministic fallback platform assignment hash seed"
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
    OPENWA_URL: str = Field(default="http://localhost:2785", validation_alias=AliasChoices("RAILTWIN_OPENWA_URL", "OPENWA_URL"), description="OpenWA Gateway Base URL")
    OPENWA_API_KEY: str = Field(default="", validation_alias=AliasChoices("RAILTWIN_OPENWA_API_KEY", "OPENWA_API_KEY"), description="OpenWA Session API Key")
    OPENWA_SESSION_ID: str = Field(default="railtwin-alerts", validation_alias=AliasChoices("RAILTWIN_OPENWA_SESSION_ID", "OPENWA_SESSION_ID"), description="OpenWA Session ID")
    OPENWA_WEBHOOK_SECRET: str = Field(default="", validation_alias=AliasChoices("RAILTWIN_OPENWA_WEBHOOK_SECRET", "OPENWA_WEBHOOK_SECRET"), description="HMAC-SHA256 Secret for Inbound Webhook")
    PUBLIC_URL: str = Field(default="http://localhost:8000", validation_alias=AliasChoices("RAILTWIN_PUBLIC_URL", "PUBLIC_URL"), description="Public Base URL for Webhooks (e.g. ngrok / LAN IP)")
    WHATSAPP_PROVIDER: str = Field(default="openwa", validation_alias=AliasChoices("RAILTWIN_WHATSAPP_PROVIDER", "WHATSAPP_PROVIDER"), description="'openwa' or 'meta'")
    SMS_PROVIDER: str = Field(default="mock", validation_alias=AliasChoices("RAILTWIN_SMS_PROVIDER", "SMS_PROVIDER"), description="'msg91', 'fast2sms', or 'mock'")
    SMS_API_KEY: str = Field(default="", validation_alias=AliasChoices("RAILTWIN_SMS_API_KEY", "SMS_API_KEY"), description="SMS Fallback API Key")
    SMS_SENDER_ID: str = Field(default="RLTWIN", validation_alias=AliasChoices("RAILTWIN_SMS_SENDER_ID", "SMS_SENDER_ID"), description="Sender Header ID for SMS")
    NOTIFICATION_RATE_LIMIT_MINUTES: float = Field(default=2.0, validation_alias=AliasChoices("RAILTWIN_NOTIFICATION_RATE_LIMIT_MINUTES", "NOTIFICATION_RATE_LIMIT_MINUTES"), description="Max 1 alert per N minutes per staff member")

    # 10. Pipeline 07: Live Position Tracking, Context & Real Delay Attribution
    LIVE_TRACKER_INTERVAL_SECONDS: int = Field(
        default=1,
        validation_alias=AliasChoices("RAILTWIN_LIVE_TRACKER_INTERVAL_SECONDS", "LIVE_TRACKER_INTERVAL_SECONDS"),
        description="Master live tracker tick interval in seconds",
    )
    LIVE_STATION_POLL_SECONDS: int = Field(
        default=30,
        validation_alias=AliasChoices("RAILTWIN_LIVE_STATION_POLL_SECONDS", "LIVE_STATION_POLL_SECONDS"),
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
        validation_alias=AliasChoices("RAILTWIN_ATTRIBUTION_UNEXPLAINED_TOLERANCE_MIN", "ATTRIBUTION_UNEXPLAINED_TOLERANCE_MIN"),
        description="Residual tolerance before logging UNEXPLAINED cause",
    )
    WEATHER_CACHE_MINUTES: int = Field(
        default=15,
        validation_alias=AliasChoices("RAILTWIN_WEATHER_CACHE_MINUTES", "WEATHER_CACHE_MINUTES"),
        description="TTL for station weather telemetry cache in minutes",
    )
    POSITION_CACHE_TTL_SECONDS: int = Field(
        default=60,
        validation_alias=AliasChoices("RAILTWIN_POSITION_CACHE_TTL_SECONDS", "POSITION_CACHE_TTL_SECONDS"),
        description="TTL for in-memory train position cache in seconds",
    )
    LIVE_SSE_PULSE_SECONDS: int = Field(
        default=5,
        validation_alias=AliasChoices("RAILTWIN_LIVE_SSE_PULSE_SECONDS", "LIVE_SSE_PULSE_SECONDS"),
        description="Server-Sent Events streaming interval for live positions in seconds",
    )
    CONTEXT_CACHE_TTL_SECONDS: int = Field(
        default=10,
        validation_alias=AliasChoices("RAILTWIN_CONTEXT_CACHE_TTL_SECONDS", "CONTEXT_CACHE_TTL_SECONDS"),
        description="TTL for enriched operational train context cache in seconds",
    )
    CONFIDENCE_TAU_SECONDS: float = Field(
        default=120.0,
        validation_alias=AliasChoices("RAILTWIN_CONFIDENCE_TAU_SECONDS", "CONFIDENCE_TAU_SECONDS"),
        description="Characteristic decay tau in seconds for confidence exp(-Δt/τ)",
    )
    DEAD_RECKON_MIN_CONFIDENCE: float = Field(
        default=0.3,
        validation_alias=AliasChoices("RAILTWIN_DEAD_RECKON_MIN_CONFIDENCE", "DEAD_RECKON_MIN_CONFIDENCE"),
        description="Confidence threshold below which position is marked STALE",
    )


# Singleton instance
settings = Settings()

if __name__ == "__main__":
    print("=== RailTwin-X Dynamic Settings ===")
    print(f"App Name: {settings.APP_NAME}")
    print(f"Database Path: {settings.DB_PATH}")
    print(f"Quantile Alphas: {settings.QUANTILE_ALPHAS}")
    print(f"Conformal Coverage Target: {(1 - settings.CONFORMAL_MISCOVERAGE_ALPHA)*100:.0f}%")
    print(f"Quality Gate Max Delay: {settings.MAX_SANITY_DELAY_MINUTES} min")
    print(f"Crew Duty Cap: {settings.CREW_DUTY_HOURS_CAP} hours")
    print(f"Live Tracker Interval: {settings.LIVE_TRACKER_INTERVAL_SECONDS}s")
    print(f"Live Station Poll: {settings.LIVE_STATION_POLL_SECONDS}s")
    print(f"Attribution Delta Min: {settings.ATTRIBUTION_DELTA_MIN}m")

