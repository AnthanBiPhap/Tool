"""
Localization Manager Module
==========================

This module provides centralized localization support for TikTokSage application.
It handles loading language files, switching languages, and retrieving localized strings.

Features
--------
- Thread-safe operations for getting localized text
- Fallback to English when translation is missing
- Support for multiple languages via JSON files
- Dynamic language switching without restart
- Nested key support with dot notation

Usage
-----
from src.utils.tiktoksage_localization import LocalizationManager

# Get localized text
text = LocalizationManager.get_text("download.ready")
button_text = LocalizationManager.get_text("buttons.download")

# Change language
LocalizationManager.set_language("es")

# Get available languages
languages = LocalizationManager.get_available_languages()
"""

import json
import threading
from pathlib import Path
from typing import Any, Dict

from src.utils.tiktoksage_logger import logger


class LocalizationManager:
    """
    Thread-safe localization manager for TikTokSage.
    
    Handles loading, caching, and retrieving localized strings from JSON language files.
    """
    
    _lock = threading.RLock()
    _current_language = "en"
    _languages: Dict[str, Dict[str, Any]] = {}
    _languages_dir = Path(__file__).parent.parent.parent / "languages"
    
    # Fallback English strings embedded in code
    _fallback_strings = {
        "app": {
            "title": "TikTokSage",
            "version": "v{version}",
            "ready": "Ready"
        },
        "buttons": {
            "download": "Download",
            "pause": "Pause", 
            "resume": "Resume",
            "cancel": "Cancel",
            "browse": "Browse",
            "clear": "Clear",
            "ok": "OK",
            "apply": "Apply",
            "close": "Close"
        },
        "dialogs": {
            "custom_options": "Custom Options",
            "settings": "Settings"
        },
        "tabs": {
            "cookies": "Login with Cookies",
            "custom_command": "Custom Command", 
            "proxy": "Proxy",
            "language": "Language"
        },
        "language": {
            "select_language": "Select Language:",
            "current_language": "Current language: {language}",
            "restart_required": "Language changes will take effect after restarting the application.",
            "english": "English",
            "spanish": "Español (Spanish)",
            "portuguese": "Português (Portuguese)",
            "russian": "Русский (Russian)",
            "chinese": "中文 (简体) (Chinese Simplified)",
            "german": "Deutsch (German)",
            "french": "Français (French)",
            "hindi": "हिन्दी (Hindi)",
            "indonesian": "Bahasa Indonesia (Indonesian)",
            "turkish": "Türkçe (Turkish)",
            "polish": "Polski (Polish)",
            "italian": "Italiano (Italian)",
            "arabic": "العربية (Arabic)",
            "japanese": "日本語 (Japanese)"
        },
        "download": {
            "preparing": "🚀 Preparing your download...",
            "completed": "✅ Download completed!",
        }
    }
    
    @classmethod
    def initialize(cls, language: str = "en") -> None:
        """Initialize localization system with specified language."""
        with cls._lock:
            cls._current_language = language
            cls._load_language(language)
    
    @classmethod
    def _load_language(cls, language: str) -> None:
        """Load language file from JSON."""
        with cls._lock:
            if language in cls._languages:
                return
            
            lang_file = cls._languages_dir / f"{language}.json"
            
            if lang_file.exists():
                try:
                    with open(lang_file, "r", encoding="utf-8") as f:
                        cls._languages[language] = json.load(f)
                    logger.info(f"Loaded language: {language}")
                except Exception as e:
                    logger.error(f"Error loading language file {lang_file}: {e}")
                    cls._languages[language] = cls._fallback_strings
            else:
                cls._languages[language] = cls._fallback_strings
    
    @classmethod
    def get_text(cls, key: str, **kwargs) -> str:
        """
        Get localized text for the given key with support for nested keys (dot notation).
        
        Args:
            key: Dot-separated key (e.g., "buttons.download")
            **kwargs: Format string arguments
        
        Returns:
            Localized string or fallback English string
        """
        with cls._lock:
            # Ensure current language is loaded
            if cls._current_language not in cls._languages:
                cls._load_language(cls._current_language)
            
            # Get from current language or fallback to English
            data = cls._languages.get(cls._current_language, {})
            
            # Navigate nested keys
            keys = key.split(".")
            value = data
            
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    value = None
                    break
            
            # If not found, try fallback
            if value is None:
                value = cls._fallback_strings
                for k in keys:
                    if isinstance(value, dict):
                        value = value.get(k)
                    else:
                        value = None
                        break
            
            # Return the value or the original key if not found
            if value is None:
                logger.warning(f"Missing translation key: {key}")
                return key
            
            # Format string if needed
            if isinstance(value, str) and kwargs:
                try:
                    return value.format(**kwargs)
                except KeyError as e:
                    logger.warning(f"Missing format argument for key {key}: {e}")
                    return value
            
            return value if isinstance(value, str) else key
    
    @classmethod
    def set_language(cls, language: str) -> None:
        """Switch to a different language."""
        with cls._lock:
            cls._current_language = language
            cls._load_language(language)
    
    @classmethod
    def get_current_language(cls) -> str:
        """Get the current language code."""
        with cls._lock:
            return cls._current_language
    
    @classmethod
    def get_available_languages(cls) -> Dict[str, str]:
        """Get all available languages."""
        languages = {}
        
        if cls._languages_dir.exists():
            for lang_file in cls._languages_dir.glob("*.json"):
                lang_code = lang_file.stem
                # Try to load the language name from the file
                try:
                    with open(lang_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        lang_name = data.get("language", {}).get(f"{lang_code}", lang_code)
                        languages[lang_code] = lang_name
                except Exception:
                    languages[lang_code] = lang_code
        
        return languages if languages else {"en": "English"}


# Convenience function for getting localized text
def _(key: str, **kwargs) -> str:
    """Shorthand for LocalizationManager.get_text()"""
    return LocalizationManager.get_text(key, **kwargs)
