"""
TikTokSage Application Constants

This module defines centralized constants used across the TikTokSage application.
By storing shared values in one place, it improves consistency, readability,
and maintainability of the codebase.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

# Handle resource paths for both development and installed package
def get_asset_path(asset_relative_path: str) -> Path:
    """
    Get the absolute path to an asset file, works both in development and installed package.
    
    Args:
        asset_relative_path: Relative path to the asset (e.g., "assets/Icon/icon.png")
    
    Returns:
        Path: Absolute path to the asset file
    """
    # Check if running as a frozen executable (PyInstaller, cx_Freeze, etc.)
    if getattr(sys, "frozen", False):
        # Running as a frozen executable
        # Try sys._MEIPASS first (PyInstaller)
        if hasattr(sys, "_MEIPASS"):
            asset_path = Path(sys._MEIPASS) / asset_relative_path
            if asset_path.exists():
                return asset_path
        
        # For cx_Freeze, assets are typically in lib/ directory next to the executable
        executable_dir = Path(sys.executable).parent
        
        # Try with lib/ prefix (cx_Freeze standard structure)
        asset_path = executable_dir / "lib" / asset_relative_path
        if asset_path.exists():
            return asset_path
        
        # Try directly in executable directory
        asset_path = executable_dir / asset_relative_path
        if asset_path.exists():
            return asset_path
    
    # Not frozen - try importlib.resources for installed packages
    try:
        # Use importlib.resources (standard in Python 3.9+)
        import importlib.resources as resources
        try:
            # Navigate to the package root and then to the asset
            package_path = resources.files('tiktoksage')
            asset_path = package_path / asset_relative_path
            if asset_path.is_file():
                return Path(str(asset_path))
        except (ImportError, AttributeError, FileNotFoundError):
            pass
            
    except Exception:
        pass
    
    # Fallback to relative path (for development environment)
    current_file = Path(__file__)
    # Go up from src/utils to tiktoksage root, then to asset
    tiktoksage_root = current_file.parent.parent.parent
    asset_path = tiktoksage_root / asset_relative_path
    
    return asset_path

# Assets Constants
ICON_PATH: Path = get_asset_path("assets/Icon/icon.png")
SOUND_PATH: Path = get_asset_path("assets/sound/notification.mp3")

OS_NAME: str = platform.system()  # Windows ; Darwin ; Linux

IS_FROZEN = getattr(sys, "frozen", False)
USER_HOME_DIR: Path = Path.home()

# OS Specific Constants
if OS_NAME == "Windows":
    OS_FULL_NAME: str = f"{OS_NAME} {platform.release()}"

    # Always use user data directory for app data, logs, config, and binaries
    APP_DIR: Path = Path(os.environ.get("LOCALAPPDATA", USER_HOME_DIR / "AppData" / "Local")) / "TikTokSage"
    APP_BIN_DIR: Path = APP_DIR / "bin"
    APP_DATA_DIR: Path = APP_DIR / "data"
    APP_LOG_DIR: Path = APP_DIR / "logs"
    APP_CONFIG_FILE: Path = APP_DATA_DIR / "tiktoksage_config.json"
    APP_HISTORY_FILE: Path = APP_DATA_DIR / "tiktoksage_history.json"
    APP_THUMBNAILS_DIR: Path = APP_DATA_DIR / "thumbnails"

    SUBPROCESS_CREATIONFLAGS: int = subprocess.CREATE_NO_WINDOW

elif OS_NAME == "Darwin":  # macOS
    _mac_version = platform.mac_ver()[0]
    OS_FULL_NAME: str = f"macOS {_mac_version}" if _mac_version else "macOS"

    # Always use user data directory for app data, logs, config, and binaries
    APP_DIR: Path = USER_HOME_DIR / "Library" / "Application Support" / "TikTokSage"
    APP_BIN_DIR: Path = APP_DIR / "bin"
    APP_DATA_DIR: Path = APP_DIR / "data"
    APP_LOG_DIR: Path = APP_DIR / "logs"
    APP_CONFIG_FILE: Path = APP_DATA_DIR / "tiktoksage_config.json"
    APP_HISTORY_FILE: Path = APP_DATA_DIR / "tiktoksage_history.json"
    APP_THUMBNAILS_DIR: Path = APP_DATA_DIR / "thumbnails"

    SUBPROCESS_CREATIONFLAGS: int = 0

else:  # Linux and other UNIX-like
    OS_FULL_NAME: str = f"{OS_NAME} {platform.release()}"

    # Always use user data directory for app data, logs, config, and binaries
    APP_DIR: Path = USER_HOME_DIR / ".local" / "share" / "TikTokSage"
    APP_BIN_DIR: Path = APP_DIR / "bin"
    APP_DATA_DIR: Path = APP_DIR / "data"
    APP_LOG_DIR: Path = APP_DIR / "logs"
    APP_CONFIG_FILE: Path = APP_DATA_DIR / "tiktoksage_config.json"
    APP_HISTORY_FILE: Path = APP_DATA_DIR / "tiktoksage_history.json"
    APP_THUMBNAILS_DIR: Path = APP_DATA_DIR / "thumbnails"

    SUBPROCESS_CREATIONFLAGS: int = 0

if __name__ == "__main__":
    # If this file is run directly, print directory information
    info = {
        "OS_NAME": OS_NAME,
        "OS_FULL_NAME": OS_FULL_NAME,
        "USER_HOME_DIR": str(USER_HOME_DIR),
        "APP_DIR": str(APP_DIR),
        "APP_BIN_DIR": str(APP_BIN_DIR),
        "APP_DATA_DIR": str(APP_DATA_DIR),
        "APP_LOG_DIR": str(APP_LOG_DIR),
        "APP_CONFIG_FILE": str(APP_CONFIG_FILE),
        "SUBPROCESS_CREATIONFLAGS": SUBPROCESS_CREATIONFLAGS,
    }
    for key, value in info.items():
        print(f"{key}: {value}")
else:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    APP_BIN_DIR.mkdir(parents=True, exist_ok=True)
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    APP_LOG_DIR.mkdir(parents=True, exist_ok=True)
    APP_THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
