#!/usr/bin/env python3
"""
TikTokSage - TikTok Video Downloader

A user-friendly GUI application for downloading TikTok videos.
"""

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from src.utils.tiktoksage_logger import logger
from src.core.tiktoksage_tiktokapi import check_tiktokapi_binary, setup_tiktokapi
from src.gui.tiktoksage_gui_main import TikTokSageApp


def show_error_dialog(message: str) -> None:
    """Show error dialog."""
    error_dialog = QMessageBox()
    error_dialog.setIcon(QMessageBox.Icon.Critical)
    error_dialog.setText("Application Error")
    error_dialog.setInformativeText(message)
    error_dialog.setWindowTitle("Error")
    error_dialog.exec()


def main() -> None:
    """Main entry point for TikTokSage."""
    try:
        logger.info("Starting TikTokSage application")
        app = QApplication(sys.argv)

        # Check for TikTokApi
        if not check_tiktokapi_binary():
            logger.warning("TikTokApi not found, starting setup process")
            result = setup_tiktokapi()
            if result != "ok":
                logger.error("TikTokApi setup failed")
                show_error_dialog(
                    "TikTokApi is required to use TikTokSage.\n"
                    "Please install it using: pip install TikTokApi"
                )
                sys.exit(1)

        # Create and show main window
        window = TikTokSageApp()
        window.show()
        
        logger.info("Application window shown, entering main loop")
        sys.exit(app.exec())
        
    except Exception as e:
        logger.critical(f"Critical application error: {e}", exc_info=True)
        show_error_dialog(f"Critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
