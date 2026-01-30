"""
Update Dialog

Dialog for update notifications.
"""

from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from .tiktoksage_dialogs_base import BaseTikTokDialog


class TikTokUpdateDialog(BaseTikTokDialog):
    """Dialog for update notifications."""
    
    def __init__(self, parent=None, new_version=""):
        super().__init__(parent, "Update Available")
        self.new_version = new_version
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        label = QLabel(f"A new version ({self.new_version}) is available!")
        layout.addWidget(label)
        
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
