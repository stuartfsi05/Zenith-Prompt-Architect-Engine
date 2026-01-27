import os
import sys
from unittest.mock import MagicMock

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.config import Config

@pytest.fixture
def mock_env(monkeypatch):
    """Sets up environment variables for testing."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test_key")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("TEMPERATURE", "0.5")
    monkeypatch.setenv("SYSTEM_PROMPT_PATH", "test/prompts/system.md")

@pytest.fixture
def mock_config(mock_env):
    """Returns a loaded Config object with mock values."""
    return Config.load()
