import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.agent import ZenithAgent

@pytest.fixture
def mock_agent_deps():
    with patch("src.core.agent.StrategicAnalyzer") as MockAnalyzer, \
         patch("src.core.agent.SemanticValidator") as MockValidator, \
         patch("src.core.agent.TheJudge") as MockJudge, \
         patch("src.core.agent.StrategicKnowledgeBase") as MockKB, \
         patch("src.core.agent.StrategicMemory") as MockMemory, \
         patch("src.core.agent.DatabaseManager") as MockDB, \
         patch("src.core.agent.GoogleGenAIProvider") as MockLLM:
        
        yield {
            "analyzer": MockAnalyzer,
            "validator": MockValidator,
            "judge": MockJudge,
            "kb": MockKB,
            "memory": MockMemory,
            "db": MockDB,
            "llm": MockLLM
        }

@pytest.mark.asyncio
async def test_agent_initialization(mock_config, mock_agent_deps):
    """Test proper initialization of Agent components."""
    agent = ZenithAgent(mock_config, "System Prompt")
    
    assert agent.config == mock_config
    mock_agent_deps["llm"].assert_called()
    mock_agent_deps["db"].return_value.create_session.assert_called()

@pytest.mark.asyncio
async def test_start_chat_restores_history(mock_config, mock_agent_deps):
    """Test that start_chat loads history from DB."""
    agent = ZenithAgent(mock_config, "System Prompt")
    
    # Mock DB history
    mock_db_instance = mock_agent_deps["db"].return_value
    mock_db_instance.get_history.return_value = [
        {"role": "user", "parts": ["Hello"]},
        {"role": "model", "parts": ["Hi"]}
    ]
    
    agent.start_chat("test_session")
    
    mock_db_instance.get_history.assert_called_with("test_session")
    mock_agent_deps["llm"].return_value.start_chat.assert_called()
    
    # Verify history formatting passed to start_chat
    call_args = mock_agent_deps["llm"].return_value.start_chat.call_args
    assert len(call_args.kwargs["history"]) == 2

@pytest.mark.asyncio
async def test_run_analysis_flow(mock_config, mock_agent_deps):
    """Test the end-to-end analysis and generation flow."""
    agent = ZenithAgent(mock_config, "Prompt")
    agent.start_chat()
    # Happy path mocks
    mock_agent_deps["validator"].return_value.validate_user_input.return_value = True
    
    mock_agent_deps["analyzer"].return_value.analyze_intent_async = AsyncMock(return_value={
        "natureza": "Raciocínio", "complexidade": "Simples"
    })
    
    mock_agent_deps["kb"].return_value.retrieve_async = AsyncMock(return_value="Contexto")
    mock_agent_deps["memory"].return_value.extract_entities_async = AsyncMock()
    mock_agent_deps["memory"].return_value.consolidate_memory_async = AsyncMock()
    
    mock_agent_deps["validator"].return_value.validate.return_value = True
    
    mock_agent_deps["kb"].return_value.retrieve_async = AsyncMock(return_value="Contexto")
    
    mock_agent_deps["validator"].return_value.validate.return_value = True
    
    # Mock LLM Stream
    async def async_gen():
        yield MagicMock(text="Response part 1")
        yield MagicMock(text="Response part 2")
    
    mock_agent_deps["llm"].return_value.send_message_async.return_value = async_gen()
    
    # Mock Judge (Pass)
    mock_agent_deps["judge"].return_value.evaluate_async = AsyncMock(return_value={
        "score": 90, "needs_refinement": False
    })

    # Collect generator output
    chunks = []
    async for chunk in agent.run_analysis_async("Hello"):
        chunks.append(chunk)

    assert len(chunks) == 2
    assert "Response part 1" in chunks
    mock_agent_deps["analyzer"].return_value.analyze_intent_async.assert_called()
    mock_agent_deps["db"].return_value.log_interaction.assert_called()
