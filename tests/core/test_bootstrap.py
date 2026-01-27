import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.core.bootstrap import BootstrapService

@pytest.mark.asyncio
async def test_bootstrap_initialization_success(mock_config):
    """Test successful initialization."""
    with patch("src.core.bootstrap.os.path.exists", return_value=True):
        with patch("src.core.bootstrap.check_knowledge_updates", return_value=False):
            result = await BootstrapService.initialize(mock_config)
            assert result is True

@pytest.mark.asyncio
async def test_bootstrap_initialization_failure(mock_config):
    """Test initialization failure handling."""
    with patch("src.core.bootstrap.check_knowledge_updates", side_effect=Exception("DB Error")):
        result = await BootstrapService.initialize(mock_config)
        assert result is False

@pytest.mark.asyncio
async def test_ensure_knowledge_consistency_update_needed(mock_config):
    """Test knowledge update flow."""
    with patch("src.core.bootstrap.check_knowledge_updates", return_value=True):
        with patch("src.core.bootstrap.run_ingestion", return_value=True) as mock_ingest:
            with patch("src.core.bootstrap.save_knowledge_hash") as mock_save:
                await BootstrapService._ensure_knowledge_consistency(mock_config)
                mock_ingest.assert_called_once()
                mock_save.assert_called_once()
