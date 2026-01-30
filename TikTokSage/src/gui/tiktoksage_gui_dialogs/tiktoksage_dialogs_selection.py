"""
Playlist Selection Dialog

Dialog for selecting items from a collection.
"""

from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from .tiktoksage_dialogs_base import BaseTikTokDialog


class PlaylistSelectionDialog(BaseTikTokDialog):
    """Dialog for playlist/collection selection."""
    
    def __init__(self, parent=None):
        super().__init__(parent, "Select Items")
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        label = QLabel("Item selection will be added here")
        layout.addWidget(label)
        
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
