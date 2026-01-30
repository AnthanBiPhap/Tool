"""
Custom Options Dialog

Dialog for custom download options.
"""

from PySide6.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout
from .tiktoksage_dialogs_base import BaseTikTokDialog


class CustomOptionsDialog(BaseTikTokDialog):
    """Dialog for custom options."""
    
    def __init__(self, parent=None):
        super().__init__(parent, "Custom Options")
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        label = QLabel("Custom download options will be added here")
        layout.addWidget(label)
        
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
