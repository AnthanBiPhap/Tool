"""
History Dialog

Dialog for viewing download history with modern card-based UI.
"""

from io import BytesIO
from pathlib import Path
from datetime import datetime

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QScrollArea,
    QWidget,
    QFrame,
    QMessageBox,
    QMenu,
)

from .tiktoksage_dialogs_base import BaseTikTokDialog
from src.utils.tiktoksage_history_manager import HistoryManager
from src.utils.tiktoksage_logger import logger


class HistoryEntryWidget(QFrame):
    """Widget representing a single history entry with thumbnail and details."""
    
    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.entry_id = entry.get("id", "")
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI for this history entry."""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 15px;
                margin: 8px;
            }
            QFrame:hover {
                background-color: #333333;
                border-color: #505050;
            }
        """)
        
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Thumbnail
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(320, 240)  # Larger height
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                border: 1px solid #404040;
                border-radius: 4px;
                background-color: #1a1a1a;
            }
        """)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setScaledContents(True)
        
        self.load_thumbnail()
        main_layout.addWidget(self.thumbnail_label, alignment=Qt.AlignmentFlag.AlignTop)
        
        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        # Title
        title = self.entry.get("title", "Unknown Title")
        self.title_label = QLabel(title)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
            }
        """)
        info_layout.addWidget(self.title_label)
        
        # URL (truncated)
        url = self.entry.get("url", "N/A")
        if len(url) > 50:
            url = url[:47] + "..."
        url_label = QLabel(f"URL: {url}")
        url_label.setStyleSheet("color: #999999; font-size: 10px;")
        info_layout.addWidget(url_label)
        
        # Date
        date_str = self.entry.get("timestamp", "Unknown")
        if date_str:
            date_label = QLabel(f"Downloaded: {date_str}")
            date_label.setStyleSheet("color: #777777; font-size: 10px;")
            info_layout.addWidget(date_label)
        
        # Format info (if available)
        file_format = self.entry.get("format", "")
        if file_format:
            format_label = QLabel(f"Format: {file_format}")
            format_label.setStyleSheet("""
                QLabel {
                    background-color: #ff0000;
                    color: white;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-size: 9px;
                    font-weight: bold;
                    width: fit-content;
                }
            """)
            info_layout.addWidget(format_label)
        
        info_layout.addStretch()
        main_layout.addLayout(info_layout, 1)
        
        # Menu button
        self.menu_button = QPushButton("⋮")
        self.menu_button.setFixedSize(50, 50)
        self.menu_button.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 20px;
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #ff0000;
            }
        """)
        self.menu_button.clicked.connect(self.show_menu)
        main_layout.addWidget(self.menu_button, alignment=Qt.AlignmentFlag.AlignTop)
    
    def load_thumbnail(self):
        """Load and display the thumbnail."""
        thumbnail_url = self.entry.get("thumbnail_url")
        
        if not thumbnail_url:
            self.set_placeholder_thumbnail()
            return
        
        # Try to download thumbnail
        try:
            import requests
            response = requests.get(thumbnail_url, timeout=5)
            response.raise_for_status()
            
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            
            if not pixmap.isNull():
                self.thumbnail_label.setPixmap(pixmap)
            else:
                self.set_placeholder_thumbnail()
        except Exception as e:
            logger.debug(f"Error loading thumbnail: {e}")
            self.set_placeholder_thumbnail()
    
    def set_placeholder_thumbnail(self):
        """Set a placeholder when thumbnail is not available."""
        self.thumbnail_label.setText("🎵")
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                border: 1px solid #404040;
                border-radius: 4px;
                background-color: #1a1a1a;
                font-size: 48px;
            }
        """)
    
    def show_menu(self):
        """Show context menu for this entry."""
        menu = QMenu(self)
        
        delete_action = menu.addAction("Delete from History")
        delete_action.triggered.connect(self.delete_entry)
        
        redownload_action = menu.addAction("Redownload")
        redownload_action.triggered.connect(self.redownload_entry)
        
        menu.exec(self.menu_button.mapToGlobal(self.menu_button.rect().bottomRight()))
    
    def delete_entry(self):
        """Delete this history entry."""
        try:
            HistoryManager.delete_entry(self.entry_id)
            self.setVisible(False)
            self.deleteLater()
            logger.info(f"Deleted history entry: {self.entry_id}")
        except Exception as e:
            logger.error(f"Error deleting entry: {e}")
            QMessageBox.warning(self, "Error", f"Failed to delete entry: {e}")
    
    def redownload_entry(self):
        """Redownload this entry."""
        QMessageBox.information(
            self,
            "Redownload",
            "Redownload feature coming soon!\n\nURL: " + self.entry.get("url", "N/A")
        )


class HistoryDialog(BaseTikTokDialog):
    """Dialog for viewing history with modern card-based layout."""
    
    def __init__(self, parent=None):
        super().__init__(parent, "Download History")
        self.setMinimumSize(800, 600)
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title_label = QLabel("Download History")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Scroll area for history entries
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #1a1a1a;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2a2a2a;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background-color: #404040;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #505050;
            }
        """)
        
        # Container widget for history entries
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(15)
        container_layout.setContentsMargins(10, 10, 10, 10)
        
        # Load and display history entries
        history = HistoryManager.get_all_entries()
        
        if history:
            for entry in history:
                entry_widget = HistoryEntryWidget(entry, self)
                container_layout.addWidget(entry_widget)
        else:
            no_history_label = QLabel("No download history yet")
            no_history_label.setStyleSheet("""
                QLabel {
                    color: #666666;
                    font-size: 14px;
                    padding: 20px;
                }
            """)
            no_history_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addWidget(no_history_label)
        
        container_layout.addStretch()
        scroll_area.setWidget(container)
        layout.addWidget(scroll_area)
        
        # Close button
        button_layout = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        close_btn.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
