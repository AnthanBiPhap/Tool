"""
Config Manager Module
=====================

This module provides **thread-safe** centralized management for application
configuration in TikTokSage. It handles reading, writing, and managing settings
stored in a JSON file, with support for nested keys via dot notation.

Thread safety is ensured using a reentrant lock (`RLock`), so multiple threads
can safely access or modify settings concurrently.

Features
--------
- Thread-safe operations for getting, setting, and deleting configuration values.
- Loads settings from a JSON config file (`APP_CONFIG_FILE`).
- Creates the config file with default values if missing or corrupt.
- Retrieves, sets, and deletes settings using dot-separated keys.
- Provides safe error handling with logging instead of raising exceptions.
- Persists updates back to disk automatically.

Usage
-----
from src.utils.tiktoksage_config_manager import ConfigManager

# Load settings (auto-loads if not already loaded)
download_path = ConfigManager.get("download_path")

# Update a value
ConfigManager.set("download_path", "D:/Downloads")

# Retrieve nested value
last_check = ConfigManager.get("cached_versions.ytdlp.last_check")

# Delete a key
ConfigManager.delete("cached_versions.ffmpeg.path")

Design Notes
------------
- Settings are stored in `ConfigManager.settings` (a dict).
- Default values are defined in `ConfigManager.default_config`.
- All modifications trigger a save (`_save`) to keep JSON in sync.
- Logs actions and errors using the app's central logger.
- Uses `RLock` to allow safe concurrent access from multiple threads.

Exceptions
----------
- Any issues during file I/O (permissions, disk errors, JSON corruption)
  are caught and logged. The application continues running with defaults
  when possible.
"""

import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from src.utils.tiktoksage_constants import APP_CONFIG_FILE, USER_HOME_DIR
from src.utils.tiktoksage_logger import logger


class ConfigManager:
    """
    Thread-safe configuration manager for TikTokSage.

    Provides methods to load, save, get, set, and delete settings stored in a JSON file.
    Supports nested keys via dot notation and automatically persists changes.
    """

    _lock: threading.RLock = threading.RLock()
    _config_file: Path = APP_CONFIG_FILE
    _settings: Dict[str, Any] = {}
    _default_config: Dict[str, Any] = {
        "download_path": str(USER_HOME_DIR / "Downloads"),
        "speed_limit_value": None,
        "speed_limit_unit_index": 0,
        "cookie_source": "browser",  # "browser" or "file"
        "cookie_browser": "chrome",
        "cookie_browser_profile": "",
        "cookie_file_path": None,
        "cookie_active": False,  # True only if user explicitly applied cookies
        "proxy_url": None,
        "geo_proxy_url": None,
        "language": "en",
        "auto_update_check": True,
        "force_output_format": False,
        "preferred_output_format": "mp4",
        "force_audio_format": False,
        "preferred_audio_format": "best",
        "cached_versions": {
            "ytdlp": {
                "version": None,
                "path": None,
                "last_check": 0,
                "path_mtime": 0,
            },
            "ffmpeg": {
                "version": None,
                "path": None,
                "last_check": 0,
                "path_mtime": 0,
            },
        },
    }
    _loaded: bool = False

    @classmethod
    def _load(cls) -> None:
        """
        Loads configuration from a JSON file if it exists and is valid.
        If the file is missing or corrupt, initializes with default values.
        Logs actions and errors during the process.
        """
        with cls._lock:
            if cls._loaded:
                return

            if cls._config_file.exists():
                try:
                    with open(cls._config_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Ensure it's a dict
                        if isinstance(data, dict):
                            # Merge with defaults to ensure all keys exist
                            cls._settings = {**cls._default_config, **data}
                        else:
                            logger.warning("Invalid config format, using defaults")
                            cls._settings = cls._default_config.copy()
                except json.JSONDecodeError:
                    logger.warning(f"Corrupt config file {cls._config_file}, using defaults")
                    cls._settings = cls._default_config.copy()
                except Exception as e:
                    logger.error(f"Error loading config: {e}")
                    cls._settings = cls._default_config.copy()
            else:
                logger.info("Config file not found, creating with defaults")
                cls._settings = cls._default_config.copy()
                cls._save()

            cls._loaded = True
            logger.info(f"Configuration loaded from {cls._config_file}")

    @classmethod
    def _save(cls) -> None:
        """Save current settings to the config file."""
        with cls._lock:
            try:
                cls._config_file.parent.mkdir(parents=True, exist_ok=True)
                with open(cls._config_file, "w", encoding="utf-8") as f:
                    json.dump(cls._settings, f, indent=2, ensure_ascii=False)
                logger.debug(f"Configuration saved to {cls._config_file}")
            except Exception as e:
                logger.error(f"Error saving config: {e}")

    @classmethod
    def get(cls, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        Get a configuration value using dot-separated keys for nested access.

        Args:
            key: The configuration key (e.g., "download_path" or "cached_versions.ytdlp.version")
            default: Default value if key doesn't exist

        Returns:
            The configuration value or the default value
        """
        with cls._lock:
            if not cls._loaded:
                cls._load()

            # Handle nested keys with dot notation
            keys = key.split(".")
            value = cls._settings

            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default

            return value if value is not None else default

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """
        Set a configuration value using dot-separated keys for nested access.

        Args:
            key: The configuration key (e.g., "download_path" or "cached_versions.ytdlp.version")
            value: The value to set
        """
        with cls._lock:
            if not cls._loaded:
                cls._load()

            # Handle nested keys with dot notation
            keys = key.split(".")
            current = cls._settings

            # Navigate/create nested structure
            for k in keys[:-1]:
                if k not in current or not isinstance(current[k], dict):
                    current[k] = {}
                current = current[k]

            # Set the final value
            current[keys[-1]] = value
            cls._save()
            logger.debug(f"Configuration updated: {key} = {value}")

    @classmethod
    def delete(cls, key: str) -> None:
        """
        Delete a configuration key.

        Args:
            key: The configuration key (e.g., "cached_versions.ffmpeg.path")
        """
        with cls._lock:
            if not cls._loaded:
                cls._load()

            # Handle nested keys with dot notation
            keys = key.split(".")
            current = cls._settings

            # Navigate to parent
            for k in keys[:-1]:
                if k in current and isinstance(current[k], dict):
                    current = current[k]
                else:
                    return  # Key doesn't exist

            # Delete the final key
            if keys[-1] in current:
                del current[keys[-1]]
                cls._save()
                logger.debug(f"Configuration key deleted: {key}")

    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all configuration settings."""
        with cls._lock:
            if not cls._loaded:
                cls._load()
            return cls._settings.copy()

    @classmethod
    def reset_to_defaults(cls) -> None:
        """Reset all settings to default values."""
        with cls._lock:
            cls._settings = cls._default_config.copy()
            cls._save()
            logger.info("Configuration reset to defaults")
