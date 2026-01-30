"""
TikTok Core Utilities Module

Provides utility functions for TikTok video handling including:
- Video URL validation
- Download path management
- Error parsing and handling
- FFmpeg integration
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, version as importlib_version
from pathlib import Path
from typing import Any, Dict, Optional, Union

import requests
from packaging import version

from src.core.tiktoksage_tiktokapi import check_tiktokapi_installed
from src.utils.tiktoksage_constants import (
    APP_CONFIG_FILE,
    OS_NAME,
    SUBPROCESS_CREATIONFLAGS,
    USER_HOME_DIR,
)
from src.utils.tiktoksage_localization import _
from src.utils.tiktoksage_logger import logger


def validate_tiktok_url(url: str) -> bool:
    """
    Validate if the URL is a valid TikTok URL.
    
    Args:
        url: URL to validate
    
    Returns:
        True if valid TikTok URL, False otherwise
    """
    tiktok_patterns = [
        r"(?:https?://)?(?:www\.)?tiktok\.com/@[\w.-]+/video/\d+",
        r"(?:https?://)?(?:www\.)?tiktok\.com/@[\w.-]+",
        r"(?:https?://)?(?:vt\.)?tiktok\.com/[\w]+",  # Short links
    ]
    
    for pattern in tiktok_patterns:
        if re.match(pattern, url):
            return True
    return False


def load_saved_path(parent_widget=None) -> Optional[str]:
    """
    Load the saved download path from config.
    
    Args:
        parent_widget: Parent widget to attach to (optional)
    
    Returns:
        The saved download path or None
    """
    try:
        from src.utils.tiktoksage_config_manager import ConfigManager
        saved_path = ConfigManager.get("download_path")
        if saved_path:
            return saved_path
    except Exception as e:
        logger.error(f"Error loading saved path: {e}")
    
    return str(USER_HOME_DIR / "Downloads")


def save_path(path: str) -> None:
    """
    Save the download path to config.
    
    Args:
        path: Path to save
    """
    try:
        from src.utils.tiktoksage_config_manager import ConfigManager
        ConfigManager.set("download_path", path)
    except Exception as e:
        logger.error(f"Error saving path: {e}")


def check_ffmpeg() -> bool:
    """
    Check if FFmpeg is available on the system.
    
    Returns:
        True if FFmpeg is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=SUBPROCESS_CREATIONFLAGS,
            timeout=5,
        )
        return result.returncode == 0
    except Exception as e:
        logger.debug(f"FFmpeg check failed: {e}")
        return False


def get_version(package_name: str) -> str:
    """
    Get the version of a package.
    
    Args:
        package_name: Name of the package
    
    Returns:
        Version string or "unknown"
    """
    try:
        return importlib_version(package_name)
    except PackageNotFoundError:
        logger.warning(f"Package {package_name} not found")
        return "unknown"


def parse_tiktok_error(error_output: str) -> str:
    """
    Parse TikTok API error messages and return user-friendly messages.
    
    Args:
        error_output: Error output from TikTok API
    
    Returns:
        User-friendly error message
    """
    error_lower = error_output.lower()
    
    # Common error patterns
    error_patterns = {
        "rate limit": _("errors.rate_limit"),
        "unauthorized": _("errors.unauthorized"),
        "forbidden": _("errors.forbidden"),
        "not found": _("errors.not_found"),
        "private": _("errors.private_video"),
        "age restricted": _("errors.age_restricted"),
        "removed": _("errors.removed_video"),
    }
    
    for pattern, message in error_patterns.items():
        if pattern in error_lower:
            return message
    
    return _("errors.unknown_error")


def should_check_for_auto_update() -> bool:
    """
    Check if we should check for auto-updates.
    
    Returns:
        True if auto-update checking is enabled, False otherwise
    """
    try:
        from src.utils.tiktoksage_config_manager import ConfigManager
        import time
        
        last_check = ConfigManager.get("cached_versions.tiktokapi.last_check", 0)
        current_time = time.time()
        
        # Check every 24 hours
        return (current_time - last_check) > (24 * 3600)
    except Exception:
        return False
