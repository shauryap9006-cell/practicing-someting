"""WO-08: Gate reproducer for secrets hardening and security checklist.

Tests that:
1. docker-compose.yml does not expose hardcoded fallback JWT secrets.
2. config.py Settings rejects default/insecure JWT keys in production mode,
   including keys with 'insecure', 'default', 'changeme', or placeholder patterns.
3. SECURITY-CHECKLIST.md exists and documents human credential rotation instructions.
"""

from pathlib import Path
import pytest
from pydantic import ValidationError
from config import Settings, BASE_DIR


def test_docker_compose_has_no_insecure_fallback_jwt_secret():
    """docker-compose.yml must not hardcode an insecure default JWT key."""
    compose_path = BASE_DIR / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist"
    content = compose_path.read_text(encoding="utf-8")
    assert "insecure_development_key_minimum_32_chars_long!" not in content, (
        "docker-compose.yml must not contain hardcoded default JWT secret"
    )
    # Ensure any JWT_SECRET_KEY line does not provide an insecure default value
    for line in content.splitlines():
        if "RAILTWIN_JWT_SECRET_KEY=" in line:
            assert ":-insecure" not in line.lower(), (
                f"docker-compose.yml must not default RAILTWIN_JWT_SECRET_KEY to an insecure value: {line}"
            )


@pytest.mark.parametrize(
    "insecure_secret",
    [
        "",  # empty
        "too_short",  # < 32 chars
        "insecure_development_key_minimum_32_chars_long!",  # former docker-compose default
        "default_jwt_secret_key_for_testing_12345678",  # contains 'default'
        "changeme_super_long_secret_key_that_is_32_chars",  # contains 'changeme'
        "replace-with-a-random-secret-at-least-32-characters",  # .env.example placeholder
        "dummy_secret_value_for_production_use_only_32_chars",  # contains 'dummy'
    ],
)
def test_production_mode_rejects_insecure_jwt_secrets(insecure_secret):
    """Production mode must reject empty, short, or placeholder/insecure JWT keys."""
    # Production configuration with all production invariants satisfied except the secret
    prod_kwargs = {
        "ENV": "production",
        "JWT_SECRET_KEY": insecure_secret,
        "DEMO_ALLOW_CLOCK_CONTROL": False,
        "ALLOW_SYNTHETIC_FALLBACK": False,
        "DEFAULT_CLOCK_MODE": "live",
        "CORS_ORIGINS": ["https://railtwin.indianrailways.gov.in"],
        "PUBLIC_URL": "https://railtwin.indianrailways.gov.in",
        "NOTIFY_DEMO_MODE": False,
        "OPENWA_WEBHOOK_SECRET": "test_webhook_secret_32_chars_long!",
    }
    with pytest.raises((ValueError, ValidationError)) as exc_info:
        Settings(**prod_kwargs)
    assert "RAILTWIN_JWT_SECRET_KEY" in str(exc_info.value) or "secret" in str(exc_info.value).lower()


def test_production_mode_accepts_valid_high_entropy_secret():
    """Production mode accepts a genuine high-entropy secret >= 32 chars without insecure patterns."""
    valid_secret = "xK9#mQ2$vL8*pZ5!nB4^wR7@yT1&uC6~eF3+jH0="
    prod_kwargs = {
        "ENV": "production",
        "JWT_SECRET_KEY": valid_secret,
        "DEMO_ALLOW_CLOCK_CONTROL": False,
        "ALLOW_SYNTHETIC_FALLBACK": False,
        "DEFAULT_CLOCK_MODE": "live",
        "CORS_ORIGINS": ["https://railtwin.indianrailways.gov.in"],
        "PUBLIC_URL": "https://railtwin.indianrailways.gov.in",
        "NOTIFY_DEMO_MODE": False,
        "OPENWA_WEBHOOK_SECRET": "test_webhook_secret_32_chars_long!",
    }
    cfg = Settings(**prod_kwargs)
    assert cfg.JWT_SECRET_KEY == valid_secret


def test_security_checklist_exists_and_contains_mandatory_human_steps():
    """SECURITY-CHECKLIST.md must exist and detail rotation & git-filter-repo commands."""
    checklist_path = BASE_DIR / "SECURITY-CHECKLIST.md"
    assert checklist_path.exists(), "SECURITY-CHECKLIST.md must exist in root"
    text = checklist_path.read_text(encoding="utf-8")
    assert "firebase-admin.json" in text
    assert "git filter-repo" in text or "git-filter-repo" in text
    assert "Google Cloud" in text or "GCP" in text
    assert "RAILTWIN_JWT_SECRET_KEY" in text
