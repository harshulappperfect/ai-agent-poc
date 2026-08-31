"""Automated test suite for MemoryManager, persistent conversational memory,
and Gemini memory compression/compaction logic.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.agent import FinanceAgent, MEMORY_COMPRESSION_THRESHOLD
from app.memory import MemoryManager


@pytest.fixture
def temp_memory_file(tmp_path: Path) -> Path:
    """Fixture providing a temporary JSON file path for memory testing."""
    return tmp_path / "memory" / "conversation.json"


def test_memory_manager_init_and_file_creation(temp_memory_file: Path):
    """Verify MemoryManager creates directory and conversation.json on init."""
    assert not temp_memory_file.exists()
    mm = MemoryManager(filepath=temp_memory_file)
    
    assert temp_memory_file.exists()
    data = mm.load_memory()
    assert data["version"] == 1
    assert data["summary"] == ""
    assert data["messages"] == []
    assert data["archive"] == []
    assert data["metadata"]["compression_count"] == 0


def test_memory_manager_add_messages_and_persistence(temp_memory_file: Path):
    """Verify user and assistant messages are saved to JSON atomically."""
    mm = MemoryManager(filepath=temp_memory_file)
    mm.add_user_message("What is ORG001's March actual?")
    mm.add_assistant_message("The actual value was 98,000.")

    # Re-read raw file from disk to verify atomic persistence
    with open(temp_memory_file, "r", encoding="utf-8") as f:
        disk_data = json.load(f)

    assert len(disk_data["messages"]) == 2
    assert disk_data["messages"][0]["role"] == "user"
    assert disk_data["messages"][0]["content"] == "What is ORG001's March actual?"
    assert disk_data["messages"][1]["role"] == "assistant"
    assert disk_data["messages"][1]["content"] == "The actual value was 98,000."


def test_memory_manager_clear_memory(temp_memory_file: Path):
    """Verify clear_memory resets active state while preserving file structure."""
    mm = MemoryManager(filepath=temp_memory_file)
    mm.add_user_message("Test query")
    mm.add_assistant_message("Test response")
    mm.update_summary_and_archive("Some summary", keep_recent_count=1)
    
    mm.clear_memory()
    data = mm.load_memory()
    assert data["summary"] == ""
    assert data["messages"] == []
    assert data["archive"] == []
    assert data["metadata"]["compression_count"] == 0


def test_agent_context_building(temp_memory_file: Path):
    """Verify build_context formats summary, history, and current question correctly."""
    agent = FinanceAgent(api_key="test_key", memory_filepath=temp_memory_file)
    agent.memory_manager.data["summary"] = "ORG001 March actual is 98000."
    agent.memory_manager.add_user_message("What about April?")
    agent.memory_manager.add_assistant_message("April actual was 105,000.")

    context = agent.build_context("What is the variance?")
    assert "COMPRESSED HISTORICAL MEMORY:\nORG001 March actual is 98000." in context
    assert "RECENT CONVERSATION:" in context
    assert "User: What about April?" in context
    assert "Assistant: April actual was 105,000." in context
    assert "CURRENT USER QUESTION:\nWhat is the variance?" in context


def test_agent_persistence_across_restarts(temp_memory_file: Path):
    """Verify memory persists when creating a new FinanceAgent instance."""
    # Instance 1 saves messages
    agent1 = FinanceAgent(api_key="test_key", memory_filepath=temp_memory_file)
    agent1.memory_manager.add_user_message("Q1 query")
    agent1.memory_manager.add_assistant_message("A1 response")

    # Instance 2 (simulating app restart) loads saved state from JSON
    agent2 = FinanceAgent(api_key="test_key", memory_filepath=temp_memory_file)
    messages = agent2.memory_manager.get_all_messages()
    assert len(messages) == 2
    assert messages[0]["content"] == "Q1 query"
    assert messages[1]["content"] == "A1 response"


@pytest.mark.asyncio
async def test_compress_memory_success(temp_memory_file: Path):
    """Verify manual memory compression updates summary, archives old messages, and increments count."""
    agent = FinanceAgent(api_key="test_key", memory_filepath=temp_memory_file)
    
    # Populate memory with 6 messages
    for i in range(1, 4):
        agent.memory_manager.add_user_message(f"User question {i}")
        agent.memory_manager.add_assistant_message(f"Assistant answer {i}")

    mock_summary_response = MagicMock()
    mock_summary_response.text = "Compressed summary of past 3 user queries."

    with patch.object(
        agent.client.aio.models,
        "generate_content",
        new_callable=AsyncMock,
        return_value=mock_summary_response,
    ) as mock_gen:
        result = await agent.compress_memory()

        assert "[Memory] Conversation compressed successfully." in result
        assert agent.memory_manager.get_summary() == "Compressed summary of past 3 user queries."
        assert agent.memory_manager.get_compression_count() == 1
        
        # Verify archiving behavior: keep_recent_count=4, so older messages moved to archive
        data = agent.memory_manager.load_memory()
        assert len(data["archive"]) == 2
        assert len(data["messages"]) == 4
        mock_gen.assert_called_once()


@pytest.mark.asyncio
async def test_compress_memory_failure_does_not_corrupt_memory(temp_memory_file: Path):
    """Verify Gemini API failure during compression leaves existing memory intact."""
    agent = FinanceAgent(api_key="test_key", memory_filepath=temp_memory_file)
    agent.memory_manager.data["summary"] = "Original intact summary."
    agent.memory_manager.add_user_message("Query before fail")
    agent.memory_manager.add_assistant_message("Answer before fail")

    # Simulate Gemini API error during compression
    with patch.object(
        agent.client.aio.models,
        "generate_content",
        new_callable=AsyncMock,
        side_effect=Exception("API Quota Exceeded 429"),
    ):
        result = await agent.compress_memory()

        assert "[Error] Memory compression failed" in result
        # Verify original memory is untouched
        assert agent.memory_manager.get_summary() == "Original intact summary."
        assert len(agent.memory_manager.get_all_messages()) == 2
        assert agent.memory_manager.get_compression_count() == 0


@pytest.mark.asyncio
async def test_auto_compression_threshold_trigger(temp_memory_file: Path):
    """Verify automatic memory compression triggers when threshold is reached."""
    agent = FinanceAgent(api_key="test_key", memory_filepath=temp_memory_file)

    # Fill memory up to 29 messages (so adding 1 more in ask_async reaches 30)
    for i in range(14):
        agent.memory_manager.add_user_message(f"U{i}")
        agent.memory_manager.add_assistant_message(f"A{i}")
    agent.memory_manager.add_user_message("Extra question to make 29")

    assert len(agent.memory_manager.get_all_messages()) == 29

    mock_summary_res = MagicMock()
    mock_summary_res.text = "Auto compressed summary."

    with patch.object(agent, "_execute_mcp_chat", new_callable=AsyncMock, return_value="Final Answer"), \
         patch.object(agent.client.aio.models, "generate_content", new_callable=AsyncMock, return_value=mock_summary_res), \
         patch("app.agent.stdio_client") as mock_stdio:

        # Mock stdio client context manager
        mock_session = AsyncMock()
        mock_session.list_tools.return_value = MagicMock(tools=[])
        mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())

        with patch("app.agent.ClientSession") as mock_client_session:
            mock_client_session.return_value.__aenter__.return_value = mock_session
            
            # This request pushes total messages (30) >= threshold (30)
            response = await agent.ask_async("Trigger question")
            assert response == "Final Answer"
            assert agent.memory_manager.get_compression_count() >= 1


def test_update_summary_and_archive_preserves_messages_when_le_keep_count(temp_memory_file: Path):
    """Verify that update_summary_and_archive leaves active messages intact when total count <= keep_recent_count."""
    mm = MemoryManager(filepath=temp_memory_file)
    mm.add_user_message("Query 1")
    mm.add_assistant_message("Answer 1")

    assert len(mm.get_all_messages()) == 2
    mm.update_summary_and_archive("New summary", keep_recent_count=4)

    # Active messages must remain intact (2 messages), archive should be empty
    data = mm.load_memory()
    assert data["summary"] == "New summary"
    assert len(data["messages"]) == 2
    assert len(data["archive"]) == 0
    assert data["metadata"]["compression_count"] == 1


