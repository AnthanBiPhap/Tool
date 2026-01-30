"""
Download Settings Dialog

Dialog for download settings.
"""

from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from .tiktoksage_dialogs_base import BaseTikTokDialog


class DownloadSettingsDialog(BaseTikTokDialog):
    """Dialog for download settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent, "Download Settings")
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        label = QLabel("Download settings will be added here")
        layout.addWidget(label)
        
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
