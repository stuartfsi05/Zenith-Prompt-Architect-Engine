import pytest

from src.core.llm.google_genai import GoogleGenAIProvider, is_modern_gemini_model
from src.utils.json_utils import parse_llm_json


@pytest.mark.parametrize(
    ("model_name", "expected"),
    [
        ("gemini-3.8-flash", True),
        ("models/gemini-3.5-flash-lite", True),
        ("gemini-4-argon", True),
        ("gemini-2.5-flash", False),
        ("gemini-1.5-pro", False),
    ],
)
def test_is_modern_gemini_model(model_name: str, expected: bool):
    assert is_modern_gemini_model(model_name) is expected


def test_modern_gemini_strips_sampling_params_and_preserves_system_instruction():
    provider = GoogleGenAIProvider(
        model_name="gemini-3.8-flash",
        temperature=0.7,
        system_instruction="Be didactic.",
        thinking_level="medium",
    )
    gen_cfg = provider._build_generate_config(
        {
            "temperature": 0.9,
            "top_p": 0.95,
            "top_k": 40,
            "candidate_count": 2,
            "response_mime_type": "application/json",
        }
    )

    assert gen_cfg.temperature is None
    assert gen_cfg.top_p is None
    assert gen_cfg.top_k is None
    assert gen_cfg.candidate_count is None
    assert gen_cfg.system_instruction == "Be didactic."
    assert gen_cfg.response_mime_type == "application/json"
    assert gen_cfg.thinking_config is not None
    assert "medium" in str(gen_cfg.thinking_config.thinking_level).lower()


def test_legacy_gemini_preserves_temperature():
    provider = GoogleGenAIProvider(
        model_name="gemini-2.5-flash",
        temperature=0.3,
        system_instruction="Legacy prompt",
    )
    gen_cfg = provider._build_generate_config()
    assert gen_cfg.temperature == 0.3
    assert gen_cfg.thinking_config is None
    assert gen_cfg.system_instruction == "Legacy prompt"


def test_parse_llm_json_handles_markdown_fences_and_empty_inputs():
    assert parse_llm_json('```json\n{"score": 95}\n```') == {"score": 95}
    assert parse_llm_json("```\n[1, 2, 3]\n```") == [1, 2, 3]
    assert parse_llm_json('{"ok": true}') == {"ok": True}

    with pytest.raises(ValueError):
        parse_llm_json("")
    with pytest.raises(ValueError):
        parse_llm_json("   ")
    with pytest.raises(ValueError):
        parse_llm_json(None)
