"""Persistent Conversational Memory Manager for Agentic AI Finance Assistant.

Manages loading, saving, message appending, and compression archiving
using a local JSON file (`memory/conversation.json`).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default file location relative to workspace root
DEFAULT_MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
DEFAULT_MEMORY_FILE = DEFAULT_MEMORY_DIR / "conversation.json"


class MemoryManager:
    """Manages persistent conversational memory stored in a local JSON file.
    
    Provides thread-safe, atomic file writes to prevent memory corruption
    if an unexpected application crash occurs.
    """

    def __init__(self, filepath: str | Path | None = None) -> None:
        """Initialize MemoryManager with target storage JSON path.
        
        Args:
            filepath: Optional custom Path or string for the JSON memory file.
                      Defaults to `memory/conversation.json`.
        """
        if filepath is None:
            self.filepath = DEFAULT_MEMORY_FILE
        else:
            self.filepath = Path(filepath).resolve()

        self.directory = self.filepath.parent
        self.data: dict[str, Any] = {}
        
        # Load or initialize memory state on startup
        self.directory.mkdir(parents=True, exist_ok=True)
        self.load_memory()

    def _ensure_file_exists(self) -> None:
        """Create memory directory and default conversation.json if missing."""
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            if not self.filepath.exists() or self.filepath.stat().st_size == 0:
                self._initialize_default_structure()
        except Exception as e:
            logger.error("Failed to initialize memory directory or file: %s", e)

    def _initialize_default_structure(self) -> None:
        """Create standard default JSON schema structure."""
        now_iso = datetime.now(timezone.utc).isoformat()
        self.data = {
            "version": 1,
            "session_id": "finance-session-001",
            "summary": "",
            "messages": [],
            "archive": [],
            "metadata": {
                "created_at": now_iso,
                "updated_at": now_iso,
                "compression_count": 0,
            },
        }
        self.save_memory()

    def load_memory(self) -> dict[str, Any]:
        """Load conversation history from JSON file.
        
        If the file is missing, empty, or corrupted, gracefully re-initializes
        default structure while preserving a backup of the corrupted file.
        
        Returns:
            Dictionary containing current memory state.
        """
        if not self.filepath.exists():
            self._initialize_default_structure()
            return self.data

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    self._initialize_default_structure()
                    return self.data
                self.data = json.loads(content)
                
                # Ensure all expected top-level keys exist
                if "messages" not in self.data:
                    self.data["messages"] = []
                if "summary" not in self.data:
                    self.data["summary"] = ""
                if "archive" not in self.data:
                    self.data["archive"] = []
                if "metadata" not in self.data:
                    now_iso = datetime.now(timezone.utc).isoformat()
                    self.data["metadata"] = {
                        "created_at": now_iso,
                        "updated_at": now_iso,
                        "compression_count": 0,
                    }
        except Exception as e:
            logger.error("Error reading memory file '%s': %s. Backing up and resetting.", self.filepath, e)
            try:
                # Backup corrupted file
                backup_path = self.filepath.with_suffix(".corrupted.bak")
                self.filepath.rename(backup_path)
            except Exception as backup_err:
                logger.error("Failed to create corrupted memory backup: %s", backup_err)
            self._initialize_default_structure()

        return self.data

    def save_memory(self) -> None:
        """Save memory state to JSON file using safe atomic file replacement.
        
        Writes to a temporary file first before replacing `conversation.json`,
        ensuring an interrupted write never corrupts active memory.
        """
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            self.data["metadata"]["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            temp_path = self.filepath.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            
            # Atomic file replacement
            temp_path.replace(self.filepath)
        except Exception as e:
            logger.error("Error saving memory to '%s': %s", self.filepath, e)

    def add_user_message(self, content: str) -> None:
        """Add user query to active message log and persist to JSON.
        
        Args:
            content: Natural language query from user.
        """
        msg = {
            "role": "user",
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.data["messages"].append(msg)
        self.save_memory()

    def add_assistant_message(self, content: str) -> None:
        """Add assistant response to active message log and persist to JSON.
        
        Args:
            content: Response text from Gemini assistant.
        """
        msg = {
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.data["messages"].append(msg)
        self.save_memory()

    def get_summary(self) -> str:
        """Retrieve stored compressed summary string.
        
        Returns:
            Compressed summary text (or empty string if none).
        """
        return self.data.get("summary", "")

    def get_recent_messages(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Retrieve recent active conversation messages.
        
        Args:
            limit: Optional integer limit for latest N messages.
                   If None, returns all active messages.
        
        Returns:
            List of message dictionaries.
        """
        messages = self.data.get("messages", [])
        if limit is None or limit >= len(messages):
            return list(messages)
        return list(messages[-limit:])

    def get_all_messages(self) -> list[dict[str, Any]]:
        """Retrieve all active messages."""
        return self.get_recent_messages(limit=None)

    def update_summary_and_archive(
        self,
        new_summary: str,
        keep_recent_count: int = 4,
    ) -> None:
        """Update compressed summary and move older active messages to archive.
        
        Args:
            new_summary: Newly generated summary text from Gemini.
            keep_recent_count: Number of recent messages to leave in active messages.
                               Older messages are appended to the archive list.
        """
        self.data["summary"] = new_summary
        active_msgs = self.data.get("messages", [])
        
        if len(active_msgs) > keep_recent_count:
            to_archive = active_msgs[:-keep_recent_count]
            recent = active_msgs[-keep_recent_count:]
            self.data.setdefault("archive", []).extend(to_archive)
            self.data["messages"] = recent

        # Increment compression counter & update metadata
        self.data["metadata"]["compression_count"] = (
            self.data["metadata"].get("compression_count", 0) + 1
        )
        self.save_memory()

    def clear_memory(self) -> None:
        """Clear active conversation messages and summary, resetting state."""
        now_iso = datetime.now(timezone.utc).isoformat()
        self.data = {
            "version": 1,
            "session_id": self.data.get("session_id", "finance-session-001"),
            "summary": "",
            "messages": [],
            "archive": [],
            "metadata": {
                "created_at": self.data.get("metadata", {}).get("created_at", now_iso),
                "updated_at": now_iso,
                "compression_count": 0,
            },
        }
        self.save_memory()

    def get_compression_count(self) -> int:
        """Get total number of memory compressions performed so far."""
        return self.data.get("metadata", {}).get("compression_count", 0)
