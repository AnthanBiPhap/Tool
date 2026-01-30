"""
History Dialog

Dialog for viewing download history.
"""

from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTextEdit
from .tiktoksage_dialogs_base import BaseTikTokDialog
from src.utils.tiktoksage_history_manager import HistoryManager


class HistoryDialog(BaseTikTokDialog):
    """Dialog for viewing history."""
    
    def __init__(self, parent=None):
        super().__init__(parent, "Download History")
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        # History text display
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        
        # Load history
        history = HistoryManager.get_all_entries()
        history_str = "Download History:\n\n"
        for entry in history:
            history_str += f"Title: {entry.get('title', 'Unknown')}\n"
            history_str += f"URL: {entry.get('url', 'N/A')}\n"
            history_str += f"Date: {entry.get('timestamp', 'Unknown')}\n\n"
        
        self.history_text.setText(history_str if history_str.strip() else "No history")
        layout.addWidget(self.history_text)
        
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("Close")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
