"""
Base Dialog Module

Base class for all TikTokSage dialogs.
"""

from PySide6.QtWidgets import QDialog
from src.utils.tiktoksage_constants import ICON_PATH
from PySide6.QtGui import QIcon


class BaseTikTokDialog(QDialog):
    """Base class for TikTokSage dialogs."""
    
    def __init__(self, parent=None, title="Dialog"):
        super().__init__(parent)
        self.setWindowTitle(title)
        
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
