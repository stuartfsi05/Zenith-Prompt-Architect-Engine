import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.analyzer import StrategicAnalyzer
from src.core.config import Config

@pytest.fixture
def mock_llm_provider():
    with patch("src.core.analyzer.GoogleGenAIProvider") as MockProvider:
        mock_instance = MockProvider.return_value
        mock_instance.generate_content_async = AsyncMock()
        mock_instance.configure = MagicMock()
        yield mock_instance

@pytest.mark.asyncio
async def test_analyze_intent_success(mock_config, mock_llm_provider):
    """Test successful intent analysis."""
    analyzer = StrategicAnalyzer(mock_config)
    
    # Mocking LLM response
    mock_llm_provider.generate_content_async.return_value = '{"natureza": "Geração", "complexidade": "Simples"}'
    
    result = await analyzer.analyze_intent_async("Write a poem")
    
    assert result["natureza"] == "Geração"
    assert result["complexidade"] == "Simples"
    mock_llm_provider.generate_content_async.assert_called()

@pytest.mark.asyncio
async def test_analyze_intent_retry_logic(mock_config, mock_llm_provider):
    """Test retry logic on JSON failure."""
    analyzer = StrategicAnalyzer(mock_config)
    
    # Fail twice, succeed on third
    mock_llm_provider.generate_content_async.side_effect = [
        "invalid json",
        "broken json",
        '{"natureza": "Investigação", "complexidade": "Composta"}'
    ]
    
    result = await analyzer.analyze_intent_async("Search for info")
    
    assert result["natureza"] == "Investigação"
    assert mock_llm_provider.generate_content_async.call_count == 3

@pytest.mark.asyncio
async def test_analyze_intent_fallback(mock_config, mock_llm_provider):
    """Test fallback when all retries fail."""
    analyzer = StrategicAnalyzer(mock_config)
    
    # Fail always
    mock_llm_provider.generate_content_async.side_effect = Exception("API Error")
    
    result = await analyzer.analyze_intent_async("Do something")
    
    assert result["natureza"] == "Raciocínio" # Fallback default
    assert "Fallback" in result["intencao_sintetizada"]
