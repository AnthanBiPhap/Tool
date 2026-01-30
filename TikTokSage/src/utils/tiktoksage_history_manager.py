"""
History Manager Module
======================

This module provides **thread-safe** centralized management for download
history in TikTokSage. It handles reading, writing, and managing download history
stored in a JSON file.

Thread safety is ensured using a reentrant lock (`RLock`), so multiple threads
can safely access or modify history concurrently.

Features
--------
- Thread-safe operations for getting, adding, and removing history entries.
- Loads history from a JSON file (`APP_HISTORY_FILE`).
- Creates the history file if missing or corrupt.
- Manages download history with metadata including thumbnails, file paths, and download options.
- Provides safe error handling with logging instead of raising exceptions.
- Persists updates back to disk automatically.

Usage
-----
from src.utils.tiktoksage_history_manager import HistoryManager

# Add a download to history
HistoryManager.add_entry(
    title="Video Title",
    url="https://tiktok.com/@user/video/...",
    thumbnail_url="https://...",
    file_path="/path/to/file.mp4",
    format_id="best",
    is_audio_only=False,
    resolution="1080p",
    download_options={...}
)

# Get all history entries
history = HistoryManager.get_all_entries()

# Remove an entry
HistoryManager.remove_entry(entry_id)

# Clear all history
HistoryManager.clear_history()

Design Notes
------------
- History entries are stored in `HistoryManager._history` (a list of dicts).
- Each entry has a unique ID based on timestamp.
- All modifications trigger a save (`_save`) to keep JSON in sync.
- Logs actions and errors using the app's central logger.
- Uses `RLock` to allow safe concurrent access from multiple threads.

Exceptions
----------
- Any issues during file I/O (permissions, disk errors, JSON corruption)
  are caught and logged. The application continues running with an empty
  history when possible.
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.tiktoksage_constants import APP_HISTORY_FILE
from src.utils.tiktoksage_logger import logger


class HistoryManager:
    """
    Thread-safe history manager for TikTokSage.

    Provides methods to load, save, get, add, and remove download history entries.
    Automatically persists changes to disk.
    """

    _lock = threading.RLock()
    _history_file = APP_HISTORY_FILE
    _history: List[Dict[str, Any]] = []
    _loaded = False

    @classmethod
    def _load(cls) -> None:
        """
        Loads download history from a JSON file if it exists and is valid.
        If the file is missing or corrupt, initializes with an empty history.
        Logs actions and errors during the process.
        """
        with cls._lock:
            if cls._history_file.exists():
                try:
                    with open(cls._history_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Ensure it's a list
                        if isinstance(data, list):
                            cls._history = data
                        else:
                            logger.warning("Invalid history format, using empty history")
                            cls._history = []
                except json.JSONDecodeError:
                    logger.warning(f"Corrupt history file {cls._history_file}, using empty history")
                    cls._history = []
                except Exception as e:
                    logger.error(f"Error loading history: {e}")
                    cls._history = []
            else:
                logger.debug("History file not found, initializing empty history")
                cls._history = []

            cls._loaded = True
            logger.info(f"History loaded from {cls._history_file}")

    @classmethod
    def _save(cls) -> None:
        """Save current history to the history file."""
        with cls._lock:
            try:
                cls._history_file.parent.mkdir(parents=True, exist_ok=True)
                with open(cls._history_file, "w", encoding="utf-8") as f:
                    json.dump(cls._history, f, indent=2, ensure_ascii=False)
                logger.debug(f"History saved to {cls._history_file}")
            except Exception as e:
                logger.error(f"Error saving history: {e}")

    @classmethod
    def add_entry(
        cls,
        title: str,
        url: str,
        thumbnail_url: Optional[str] = None,
        file_path: Optional[str] = None,
        format_id: Optional[str] = None,
        is_audio_only: bool = False,
        resolution: Optional[str] = None,
        download_options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a new entry to the download history.

        Args:
            title: Video title
            url: Video URL
            thumbnail_url: URL of the video thumbnail
            file_path: Path to the downloaded file
            format_id: Format ID used for download
            is_audio_only: Whether only audio was downloaded
            resolution: Video resolution
            download_options: Dictionary of download options used

        Returns:
            The unique ID of the added entry
        """
        with cls._lock:
            if not cls._loaded:
                cls._load()

            entry_id = str(int(time.time() * 1000))  # Millisecond timestamp

            entry = {
                "id": entry_id,
                "title": title,
                "url": url,
                "thumbnail_url": thumbnail_url,
                "file_path": file_path,
                "format_id": format_id,
                "is_audio_only": is_audio_only,
                "resolution": resolution,
                "download_options": download_options or {},
                "timestamp": datetime.now().isoformat(),
            }

            cls._history.insert(0, entry)  # Add to beginning
            cls._save()
            logger.info(f"Added history entry: {title}")
            return entry_id

    @classmethod
    def get_all_entries(cls) -> List[Dict[str, Any]]:
        """Get all history entries."""
        with cls._lock:
            if not cls._loaded:
                cls._load()
            return cls._history.copy()

    @classmethod
    def get_entry(cls, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific history entry by ID."""
        with cls._lock:
            if not cls._loaded:
                cls._load()

            for entry in cls._history:
                if entry.get("id") == entry_id:
                    return entry.copy()
            return None

    @classmethod
    def remove_entry(cls, entry_id: str) -> bool:
        """
        Remove an entry from history by ID.

        Args:
            entry_id: The ID of the entry to remove

        Returns:
            True if entry was found and removed, False otherwise
        """
        with cls._lock:
            if not cls._loaded:
                cls._load()

            for i, entry in enumerate(cls._history):
                if entry.get("id") == entry_id:
                    cls._history.pop(i)
                    cls._save()
                    logger.info(f"Removed history entry: {entry_id}")
                    return True
            return False

    @classmethod
    def clear_history(cls) -> None:
        """Clear all history entries."""
        with cls._lock:
            cls._history = []
            cls._save()
            logger.info("History cleared")

    @classmethod
    def search_entries(cls, query: str) -> List[Dict[str, Any]]:
        """
        Search history entries by title or URL.

        Args:
            query: Search query string

        Returns:
            List of matching entries
        """
        with cls._lock:
            if not cls._loaded:
                cls._load()

            query_lower = query.lower()
            results = [
                entry
                for entry in cls._history
                if query_lower in entry.get("title", "").lower()
                or query_lower in entry.get("url", "").lower()
            ]
            return results
