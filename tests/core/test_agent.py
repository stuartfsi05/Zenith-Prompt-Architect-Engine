import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.agent import ZenithAgent


@pytest.fixture
def mock_dependencies():
    """Creates mock objects for all ZenithAgent DI dependencies."""
    mock_config = MagicMock()
    mock_config.MODEL_NAME = "test-model"
    
    mock_db = MagicMock()
    mock_db.log_interaction = MagicMock()
    
    mock_llm = MagicMock()
    mock_llm.start_chat = MagicMock(return_value=MagicMock())
    
    mock_kb = MagicMock()
    mock_kb.retrieve_async = AsyncMock(return_value="Contexto RAG")
    
    mock_context_builder = MagicMock()
    mock_context_builder.build_system_injection = MagicMock(return_value="System injection")
    mock_context_builder.resolve_rag_context = AsyncMock(return_value="RAG resolved")
    mock_context_builder.assemble_prompt = MagicMock(return_value="Final prompt")
    
    mock_analyzer = MagicMock()
    mock_analyzer.analyze_intent_async = AsyncMock(
        return_value={"natureza": "Raciocínio", "complexidade": "Simples"}
    )
    mock_analyzer._get_fallback_response = MagicMock(
        return_value={"natureza": "Raciocínio", "complexidade": "Simples"}
    )
    
    mock_judge = MagicMock()
    mock_judge.evaluate_async = AsyncMock(
        return_value={"score": 90, "needs_refinement": False, "feedback": "Approved."}
    )
    
    mock_memory = MagicMock()
    mock_memory.manage_history = AsyncMock()
    mock_memory.get_context_injection = MagicMock(return_value="")
    mock_memory.extract_entities_async = AsyncMock()
    
    mock_validator = MagicMock()
    mock_validator.validate_user_input = MagicMock(return_value=True)

    return {
        "config": mock_config,
        "db": mock_db,
        "llm": mock_llm,
        "kb": mock_kb,
        "context_builder": mock_context_builder,
        "analyzer": mock_analyzer,
        "judge": mock_judge,
        "memory": mock_memory,
        "validator": mock_validator,
    }


def _create_agent(deps, system_instruction="Test System Prompt"):
    """Helper to create ZenithAgent with mock deps."""
    return ZenithAgent(
        config=deps["config"],
        system_instruction=system_instruction,
        db=deps["db"],
        llm=deps["llm"],
        knowledge_base=deps["kb"],
        context_builder=deps["context_builder"],
        analyzer=deps["analyzer"],
        judge=deps["judge"],
        memory=deps["memory"],
        validator=deps["validator"],
    )


def test_agent_initialization(mock_dependencies):
    """Test proper initialization of Agent components via DI."""
    agent = _create_agent(mock_dependencies)

    assert agent.config == mock_dependencies["config"]
    assert agent.db == mock_dependencies["db"]
    assert agent.llm == mock_dependencies["llm"]
    assert agent.knowledge_base == mock_dependencies["kb"]
    assert agent.current_session_id is None
    assert agent.main_session is None


def test_agent_rejects_none_db(mock_dependencies):
    """Test that agent raises ValueError when db is None."""
    mock_dependencies["db"] = None
    with pytest.raises(ValueError, match="db"):
        _create_agent(mock_dependencies)


def test_agent_rejects_none_llm(mock_dependencies):
    """Test that agent raises ValueError when llm is None."""
    mock_dependencies["llm"] = None
    with pytest.raises(ValueError, match="llm"):
        _create_agent(mock_dependencies)


def test_start_chat_sets_session(mock_dependencies):
    """Test that start_chat initializes the chat session."""
    agent = _create_agent(mock_dependencies)
    
    # Mock history service
    agent.history_service = MagicMock()
    agent.history_service.get_formatted_history = MagicMock(return_value=[
        {"role": "user", "parts": ["Hello"]},
        {"role": "model", "parts": ["Hi"]},
    ])
    
    agent.start_chat("test_session", "test_user")

    assert agent.current_session_id == "test_session"
    agent.history_service.get_formatted_history.assert_called_with("test_session", "test_user")
    mock_dependencies["llm"].start_chat.assert_called_once()


@pytest.mark.asyncio
async def test_run_analysis_blocks_invalid_input(mock_dependencies):
    """Test that validation can block unsafe input."""
    agent = _create_agent(mock_dependencies)
    mock_dependencies["validator"].validate_user_input.return_value = False

    # Mock history service for start_chat
    agent.history_service = MagicMock()
    agent.history_service.get_formatted_history = MagicMock(return_value=[])

    chunks = []
    async for chunk in agent.run_analysis_async("bad input", user_id="u1", session_id="s1"):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert "blocked" in chunks[0].lower() or "⚠️" in chunks[0]


@pytest.mark.asyncio
async def test_run_analysis_happy_path(mock_dependencies):
    """Test the end-to-end analysis and generation flow."""
    agent = _create_agent(mock_dependencies)
    
    # Mock history service
    agent.history_service = MagicMock()
    agent.history_service.get_formatted_history = MagicMock(return_value=[])

    # Mock LLM streaming
    async def mock_stream(*args, **kwargs):
        yield "Response part 1"
        yield "Response part 2"
        yield {"usage_metadata": {"input_tokens": 10, "output_tokens": 20}}

    mock_dependencies["llm"].send_message_async = MagicMock(return_value=mock_stream())

    chunks = []
    async for chunk in agent.run_analysis_async("Hello", user_id="u1", session_id="s1"):
        chunks.append(chunk)

    # Should have response chunks + quality panel
    text_chunks = [c for c in chunks if isinstance(c, str) and "Response part" in c]
    assert len(text_chunks) == 2
    
    # Verify interaction was logged
    mock_dependencies["db"].log_interaction.assert_called()
