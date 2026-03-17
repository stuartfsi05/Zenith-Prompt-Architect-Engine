from unittest.mock import patch

import pytest

from src.core.config import Config


def test_config_load_success(mock_env):
    """Test successful loading of configuration."""
    config = Config()
    assert config.GOOGLE_API_KEY.get_secret_value() == "test_key"
    assert config.MODEL_NAME == "test-model"
    assert config.TEMPERATURE == 0.5
    assert "data" in str(config.DATA_DIR)


def test_config_missing_api_key(monkeypatch):
    """Test error when API Key is missing."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    # Prevent Pydantic Settings from loading the real .env file
    monkeypatch.setattr(Config, "model_config", {**Config.model_config, "env_file": None})
    with pytest.raises(Exception):
        Config()


def test_config_default_values(monkeypatch):
    """Test default values when env vars are missing."""
    monkeypatch.setenv("GOOGLE_API_KEY", "key")
    monkeypatch.delenv("TEMPERATURE", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)

    config = Config()
    assert config.TEMPERATURE == 0.1
    assert config.MODEL_NAME == "gemini-2.5-flash"
