"""
TikTok API Module

Handles TikTok API setup, downloads, and version management.
Uses TikTokApi library for downloading TikTok videos.
"""

import os
import subprocess
import tempfile
import time
from importlib.metadata import PackageNotFoundError, version as importlib_version
from pathlib import Path
from typing import Optional

import requests
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from src.utils.tiktoksage_logger import logger
from src.utils.tiktoksage_localization import _
from src.utils.tiktoksage_constants import (
    APP_BIN_DIR,
    ICON_PATH,
    OS_FULL_NAME,
    OS_NAME,
    SUBPROCESS_CREATIONFLAGS,
)


def check_tiktokapi_installed() -> bool:
    """
    Check if TikTokApi is installed.
    
    Returns:
        True if installed, False otherwise
    """
    try:
        import TikTokApi
        return True
    except ImportError:
        return False


def get_tiktokapi_version() -> str:
    """
    Get the version of installed TikTokApi.
    
    Returns:
        Version string or "unknown"
    """
    try:
        return importlib_version("TikTokApi")
    except PackageNotFoundError:
        return "unknown"


def install_tiktokapi() -> bool:
    """
    Install or upgrade TikTokApi package.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Installing TikTokApi package...")
        subprocess.run(
            [os.sys.executable, "-m", "pip", "install", "--upgrade", "TikTokApi"],
            check=True,
            creationflags=SUBPROCESS_CREATIONFLAGS,
        )
        logger.info("TikTokApi installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install TikTokApi: {e}")
        return False
    except Exception as e:
        logger.error(f"Error installing TikTokApi: {e}")
        return False


class TikTokApiSetupDialog(QDialog):
    """Dialog for setting up TikTok API."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TikTokApi Setup")
        self.setGeometry(100, 100, 400, 150)
        
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        label = QLabel(
            "TikTokApi is required to download TikTok videos.\n\n"
            "Click 'Install' to install TikTokApi package."
        )
        layout.addWidget(label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.install_btn = QPushButton("Install")
        self.install_btn.clicked.connect(self.on_install_click)
        button_layout.addWidget(self.install_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def on_install_click(self):
        """Handle install button click."""
        self.install_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        
        # Run installation in background
        self.install_thread = TikTokApiInstallThread()
        self.install_thread.finished.connect(self.on_install_finished)
        self.install_thread.start()
    
    def on_install_finished(self, success: bool):
        """Handle installation finished."""
        if success:
            QMessageBox.information(
                self,
                "Success",
                "TikTokApi installed successfully!",
            )
            self.accept()
        else:
            self.install_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            QMessageBox.critical(
                self,
                "Error",
                "Failed to install TikTokApi. Please install manually:\n"
                "pip install TikTokApi",
            )


class TikTokApiInstallThread(QThread):
    """Background thread for installing TikTokApi."""
    
    finished = Signal(bool)
    
    def run(self):
        """Run the installation."""
        success = install_tiktokapi()
        self.finished.emit(success)


def check_tiktokapi_binary() -> bool:
    """
    Check if TikTokApi is available.
    
    Returns:
        True if available, False otherwise
    """
    if check_tiktokapi_installed():
        logger.info(f"TikTokApi is installed (version {get_tiktokapi_version()})")
        return True
    return False


def setup_tiktokapi() -> str:
    """
    Setup TikTokApi with user dialog.
    
    Returns:
        "ok" if setup successful, "TikTokApi" otherwise
    """
    if check_tiktokapi_binary():
        return "ok"
    
    # Show setup dialog
    from PySide6.QtWidgets import QApplication
    
    app = QApplication.instance()
    if app:
        dialog = TikTokApiSetupDialog()
        result = dialog.exec()
        
        if result == QDialog.Accepted:
            if check_tiktokapi_binary():
                return "ok"
    
    return "TikTokApi"
