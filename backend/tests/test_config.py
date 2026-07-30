"""Config / security-hardening tests."""
import pytest

from app.core.config import Settings


def test_dev_allows_weak_secret():
    s = Settings(env="development", secret_key="short")
    assert s.env == "development"


def test_prod_rejects_weak_secret():
    with pytest.raises(ValueError):
        Settings(env="production", secret_key="change-me-in-prod")


def test_prod_accepts_strong_secret():
    strong = "x" * 48
    s = Settings(env="production", secret_key=strong)
    assert s.secret_key == strong


def test_sync_url_uses_psycopg():
    s = Settings(database_url="postgresql+asyncpg://u:p@h:5432/db")
    assert s.sync_database_url == "postgresql+psycopg://u:p@h:5432/db"
