import pytest
from pydantic import ValidationError

from src.core.config import Config


def test_config_defaults_and_whitespace_stripping():
    cfg = Config(
        GOOGLE_API_KEY="test-key",
        MODEL_NAME="  gemini-3.8-flash  ",
        AUX_MODEL_NAME="  gemini-3.5-flash-lite ",
    )
    assert cfg.MODEL_NAME == "gemini-3.8-flash"
    assert cfg.AUX_MODEL_NAME == "gemini-3.5-flash-lite"
    assert cfg.EMBEDDING_MODEL == "models/gemini-embedding-2"
    assert cfg.THINKING_LEVEL == "medium"
    assert cfg.AUX_THINKING_LEVEL == "minimal"
    assert cfg.DEMO_DAILY_LIMIT == 5
    assert "https://zenith-interface-ten.vercel.app" in cfg.allowed_origins_list
    assert "https://zenith-interface.vercel.app" not in cfg.allowed_origins_list


def test_allowed_origins_list_parsing():
    cfg = Config(
        GOOGLE_API_KEY="test-key",
        ALLOWED_ORIGINS=" https://app.example.com/ , http://localhost:5173/ , / , ",
    )
    assert cfg.allowed_origins_list == [
        "https://app.example.com",
        "http://localhost:5173",
    ]


def test_thinking_level_rejects_invalid_value_for_3_8():
    with pytest.raises(ValidationError):
        Config(GOOGLE_API_KEY="test-key", THINKING_LEVEL="minimal")


def test_system_prompt_path_resolution(tmp_path):
    custom = tmp_path / "custom_prompt.txt"
    custom.write_text("Custom instruction", encoding="utf-8")

    cfg = Config(GOOGLE_API_KEY="test-key", SYSTEM_PROMPT_PATH=str(custom))
    assert cfg.SYSTEM_PROMPT_PATH == custom

    cfg_missing = Config(
        GOOGLE_API_KEY="test-key", SYSTEM_PROMPT_PATH=str(tmp_path / "missing.txt")
    )
    assert cfg_missing.SYSTEM_PROMPT_PATH.exists()
