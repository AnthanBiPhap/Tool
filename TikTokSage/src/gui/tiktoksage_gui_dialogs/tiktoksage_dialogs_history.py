"""
History Dialog

Dialog for viewing download history with modern card-based UI.
"""

from io import BytesIO
from pathlib import Path
from datetime import datetime

from PIL import Image
from PySide6.QtCore import Qt, QTimer, QThread, Signal
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
    QLineEdit,
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
                padding: 12px;
                margin: 4px;
            }
            QFrame:hover {
                background-color: #333333;
                border-color: #505050;
            }
        """)
        
        main_layout = QVBoxLayout(self)  # Vertical layout for large thumbnail
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        # Thumbnail
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setMaximumSize(400, 300)  # Max size but not fixed
        self.thumbnail_label.setMinimumSize(80, 60)   # Min size
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
        main_layout.addWidget(self.thumbnail_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        
        # Title
        title = self.entry.get("title", "Unknown Title")
        self.title_label = QLabel(title)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
            }
        """)
        info_layout.addWidget(self.title_label)
        
        # Channel/Author
        url = self.entry.get("url", "")
        author = "Unknown"
        if "@" in url:
            try:
                author = url.split("@")[1].split("/")[0]
                author = f"Channel: {author}"
            except:
                author = "Channel: Unknown"
        author_label = QLabel(author)
        author_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        info_layout.addWidget(author_label)
        
        # Date and time
        timestamp = self.entry.get("timestamp", "")
        if timestamp:
            try:
                # Parse timestamp and format
                if isinstance(timestamp, str):
                    date_label = QLabel(f"Downloaded: {timestamp}")
                else:
                    date_label = QLabel(f"Downloaded: {str(timestamp)}")
            except:
                date_label = QLabel("Downloaded: Unknown")
        else:
            date_label = QLabel("Downloaded: Unknown")
        date_label.setStyleSheet("color: #999999; font-size: 11px;")
        info_layout.addWidget(date_label)
        
        # Type and size
        details_layout = QHBoxLayout()
        details_layout.setSpacing(10)
        
        # Type
        is_audio = self.entry.get("is_audio_only", False)
        type_label = QLabel("Audio" if is_audio else "Video")
        type_label.setStyleSheet("""
            QLabel {
                background-color: #007acc;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        details_layout.addWidget(type_label)
        
        # Size (calculate from file path or metadata)
        size_text = "Size: N/A"
        file_path = self.entry.get("file_path", "")
        
        # Try to get file size from actual file
        if file_path and Path(file_path).exists():
            try:
                size_bytes = Path(file_path).stat().st_size
                size_text = f"Size: {self._format_file_size(size_bytes)}"
            except Exception:
                pass
        
        # Try to get from metadata
        elif "raw_data" in self.entry and hasattr(self.entry["raw_data"], 'video'):
            try:
                # Estimate size from video metadata (rough estimate)
                duration = getattr(self.entry["raw_data"].video, 'duration', 0)
                if duration > 0:
                    # Rough estimate: 1MB per 10 seconds for TikTok videos
                    estimated_size = duration * 1024 * 1024 / 10
                    size_text = f"Size: ~{self._format_file_size(estimated_size)}"
            except Exception:
                pass
        
        size_label = QLabel(size_text)
        size_label.setStyleSheet("color: #888888; font-size: 11px;")
        details_layout.addWidget(size_label)
        
        details_layout.addStretch()
        info_layout.addLayout(details_layout)
        
        # Menu button hidden
        # self.menu_button = QPushButton("⚙")
        # self.menu_button.setFixedSize(32, 32)
        # self.menu_button.setText("⚙")  # Use gear icon - more visible
        # self.menu_button.setToolTip("Menu Options")  # Add tooltip
        # self.menu_button.setStyleSheet("""
        #     QPushButton {
        #         background-color: #404040;
        #         border: 1px solid #555555;
        #         border-radius: 16px;
        #         color: white;
        #         font-size: 18px;
        #         font-weight: bold;
        #         font-family: "Segoe UI Symbol", "Apple Color Emoji", Arial, sans-serif;
        #         text-align: center;
        #         line-height: 32px;
        #     }
        #     QPushButton:hover {
        #         background-color: #4a9eff;
        #         border-color: #6bb6ff;
        #         transform: scale(1.05);
        #     }
        #     QPushButton:pressed {
        #         background-color: #ff4444;
        #         border-color: #ff6666;
        #     }
        # """)
        # self.menu_button.clicked.connect(self.show_menu)
        # details_with_menu_layout.addWidget(self.menu_button, alignment=Qt.AlignmentFlag.AlignTop)
        
        info_layout.addLayout(details_layout)
        main_layout.addLayout(info_layout)
    
    def load_thumbnail(self):
        """Load and display the thumbnail with caching and timeout."""
        thumbnail_url = self.entry.get("thumbnail_url")
        
        if not thumbnail_url:
            self.set_placeholder_thumbnail()
            return
        
        # Set placeholder first
        self.set_placeholder_thumbnail()
        
        # Load thumbnail in background to avoid blocking UI
        from PySide6.QtCore import QThread, Signal
        
        class ThumbnailLoader(QThread):
            loaded = Signal(QPixmap)
            
            def __init__(self, url):
                super().__init__()
                self.url = url
            
            def run(self):
                try:
                    import requests
                    response = requests.get(self.url, timeout=3)  # Short timeout
                    if response.status_code == 200:
                        pixmap = QPixmap()
                        if pixmap.loadFromData(response.content) and not pixmap.isNull():
                            self.loaded.emit(pixmap)
                except Exception:
                    pass  # Keep placeholder if failed
        
        # Start background loading
        self.thumbnail_loader = ThumbnailLoader(thumbnail_url)
        self.thumbnail_loader.loaded.connect(self._on_thumbnail_loaded)
        self.thumbnail_loader.start()
    
    def _on_thumbnail_loaded(self, pixmap):
        """Handle thumbnail loaded in background with original aspect ratio."""
        if hasattr(self, 'thumbnail_label') and self.thumbnail_label:
            # Calculate scaled size maintaining aspect ratio
            original_size = pixmap.size()
            max_size = self.thumbnail_label.maximumSize()
            min_size = self.thumbnail_label.minimumSize()
            
            # Scale to fit within max size while maintaining aspect ratio
            scaled_size = original_size.scaled(max_size, Qt.AspectRatioMode.KeepAspectRatio)
            
            # Ensure minimum size
            if scaled_size.width() < min_size.width() or scaled_size.height() < min_size.height():
                scaled_size = original_size.scaled(min_size, Qt.AspectRatioMode.KeepAspectRatioByExpanding)
            
            # Set the scaled pixmap
            scaled_pixmap = pixmap.scaled(scaled_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.thumbnail_label.setPixmap(scaled_pixmap)
            self.thumbnail_label.setFixedSize(scaled_size)
    
    def _format_file_size(self, size_bytes):
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        if i == 0:
            return f"{int(size)} {size_names[i]}"
        else:
            return f"{size:.1f} {size_names[i]}"
    
    def set_placeholder_thumbnail(self):
        """Set a placeholder when thumbnail is not available."""
        self.thumbnail_label.setText("🎵")
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                border: 1px solid #404040;
                border-radius: 4px;
                background-color: #1a1a1a;
                font-size: 72px;
            }
        """)
    
    def show_menu(self):
        """Show context menu for this entry with improved styling."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 4px;
                min-width: 180px;
            }
            QMenu::item {
                background-color: transparent;
                color: #ffffff;
                padding: 8px 16px;
                border-radius: 4px;
                margin: 2px;
            }
            QMenu::item:selected {
                background-color: #4a9eff;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background-color: #404040;
                margin: 4px 8px;
            }
        """)
        
        # Delete from History with icon
        delete_action = menu.addAction("🗑️ Delete from History")
        delete_action.triggered.connect(self.delete_entry)
        
        # Add separator
        menu.addSeparator()
        
        # Redownload with icon
        redownload_action = menu.addAction("⬇️ Redownload")
        redownload_action.triggered.connect(self.redownload_entry)
        
        # Copy URL with icon
        copy_url_action = menu.addAction("📋 Copy URL")
        copy_url_action.triggered.connect(self.copy_url)
        
        # Position menu to show on the right side of the button
        button_rect = self.menu_button.rect()
        global_pos = self.menu_button.mapToGlobal(button_rect.topRight())
        menu.exec(global_pos)
    
    def copy_url(self):
        """Copy URL to clipboard."""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        url = self.entry.get("url", "")
        if url:
            clipboard.setText(url)
            # Show brief feedback
            self.menu_button.setText("✓")
            QTimer.singleShot(1000, lambda: self.menu_button.setText("⋮"))
    
    def delete_entry(self):
        """Delete this history entry."""
        try:
            HistoryManager.remove_entry(self.entry_id)
            self.setVisible(False)
            self.deleteLater()
            # Update parent's count if available
            if hasattr(self.parent(), 'update_count'):
                self.parent().update_count()
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
        self.setMinimumSize(1000, 700)  # Larger window for big thumbnails
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header with title and controls
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Download History")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #ffffff;
            }
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Clear all button
        clear_btn = QPushButton("Clear All History")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
        """)
        clear_btn.clicked.connect(self.clear_all_history)
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search history...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px 12px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4a9eff;
            }
        """)
        self.search_input.textChanged.connect(self.filter_history)
        layout.addWidget(self.search_input)
        
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
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setSpacing(10)
        self.container_layout.setContentsMargins(5, 5, 5, 5)
        
        # Initialize history entries list
        self.history_entries = []
        
        self.container_layout.addStretch()
        scroll_area.setWidget(self.container)
        layout.addWidget(scroll_area)
        
        # Footer with download count
        footer_layout = QHBoxLayout()
        self.count_label = QLabel("0 downloads")
        self.count_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 12px;
            }
        """)
        footer_layout.addWidget(self.count_label)
        footer_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(80)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)
        
        layout.addLayout(footer_layout)
        self.setLayout(layout)
        
        # Load and display history entries after all UI elements are created
        self.load_history()
    
    def load_history(self):
        """Load and display history entries with lazy loading."""
        # Clear existing widgets
        for i in reversed(range(self.container_layout.count())):
            child = self.container_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
        
        # Load history entries
        self.history_entries = []
        history = HistoryManager.get_all_entries()
        
        if history:
            # Load first 10 entries immediately, rest with delay
            initial_batch = history[:10]
            remaining_batch = history[10:]
            
            for entry in initial_batch:
                entry_widget = HistoryEntryWidget(entry, self)
                self.history_entries.append(entry_widget)
                self.container_layout.addWidget(entry_widget)
            
            # Load remaining entries with delay to prevent UI freezing
            if remaining_batch:
                self.load_remaining_entries(remaining_batch)
        else:
            no_history_label = QLabel("No download history yet")
            no_history_label.setStyleSheet("""
                QLabel {
                    color: #666666;
                    font-size: 14px;
                    padding: 40px;
                }
            """)
            no_history_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.container_layout.addWidget(no_history_label)
        
        # Update count
        self.update_count()
    
    def load_remaining_entries(self, entries):
        """Load remaining history entries with delay."""
        def load_next():
            if not entries:
                return
            
            entry = entries.pop(0)
            entry_widget = HistoryEntryWidget(entry, self)
            self.history_entries.append(entry_widget)
            self.container_layout.addWidget(entry_widget)
            
            # Update count
            self.update_count()
            
            # Load next entry after short delay
            if entries:
                QTimer.singleShot(50, load_next)  # 50ms delay between each
        
        QTimer.singleShot(100, load_next)  # Start after 100ms
    
    def update_count(self):
        """Update the download count label."""
        count = len(self.history_entries) if hasattr(self, 'history_entries') else 0
        self.count_label.setText(f"{count} downloads")
    
    def filter_history(self, text):
        """Filter history entries based on search text."""
        search_text = text.lower()
        
        for entry_widget in self.history_entries:
            title = entry_widget.entry.get("title", "").lower()
            url = entry_widget.entry.get("url", "").lower()
            
            if search_text in title or search_text in url:
                entry_widget.setVisible(True)
            else:
                entry_widget.setVisible(False)
    
    def clear_all_history(self):
        """Clear all download history."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete all download history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                HistoryManager.clear_history()
                self.load_history()
                logger.info("Cleared all download history")
            except Exception as e:
                logger.error(f"Error clearing history: {e}")
                QMessageBox.warning(self, "Error", f"Failed to clear history: {e}")
