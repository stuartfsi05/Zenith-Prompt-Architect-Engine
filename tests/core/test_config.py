import os
import pytest
from unittest.mock import patch
from src.core.config import Config

@pytest.fixture(autouse=True)
def mock_load_dotenv():
    """Prevent loading .env file during tests."""
    with patch("src.core.config.load_dotenv"):
        yield

def test_config_load_success(mock_env):
    """Test successful loading of configuration."""
    config = Config.load()
    assert config.GOOGLE_API_KEY == "test_key"
    assert config.MODEL_NAME == "test-model"
    assert config.TEMPERATURE == 0.5
    assert "data" in config.DATA_DIR

def test_config_missing_api_key(monkeypatch):
    """Test error when API Key is missing."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError):
        Config.load()

def test_config_default_values(monkeypatch):
    """Test default values when env vars are missing."""
    monkeypatch.setenv("GOOGLE_API_KEY", "key")
    monkeypatch.delenv("TEMPERATURE", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)
    
    config = Config.load()
    assert config.TEMPERATURE == 0.1
    assert config.MODEL_NAME == "gemini-2.5-flash"
