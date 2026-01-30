"""
Channel Videos Selection Dialog

Dialog for selecting videos to download from a TikTok channel.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
)

from src.gui.tiktoksage_gui_dialogs.tiktoksage_dialogs_base import BaseTikTokDialog
from src.core.tiktoksage_channel_downloader import get_channel_videos
from src.utils.tiktoksage_logger import logger


class ChannelVideosDialog(BaseTikTokDialog):
    """Dialog for selecting videos from a TikTok channel."""
    
    videos_selected = Signal(list)  # Emit list of selected video URLs
    
    def __init__(self, channel_url: str, parent=None):
        super().__init__(parent, "Select Channel Videos")
        self.channel_url = channel_url
        self.videos = []
        self.selected_urls = []  # Store selected URLs
        self.setMinimumSize(700, 500)
        
        self.init_ui()
        self.fetch_videos()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        # Info label
        info_label = QLabel("Loading videos from channel...")
        info_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        layout.addWidget(info_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)
        
        # Videos list
        self.videos_list = QListWidget()
        self.videos_list.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 4px;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #0066cc;
            }
        """)
        self.videos_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.videos_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_videos)
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all_videos)
        button_layout.addWidget(deselect_all_btn)
        
        button_layout.addStretch()
        
        download_btn = QPushButton("Download Selected")
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                padding: 5px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
        """)
        download_btn.clicked.connect(self.on_download)
        button_layout.addWidget(download_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def fetch_videos(self):
        """Fetch videos from the channel."""
        try:
            # Fetch with no limit - yt-dlp will crawl entire profile
            self.videos = get_channel_videos(self.channel_url, max_videos=0)
            
            if not self.videos:
                QMessageBox.warning(
                    self,
                    "No Videos Found",
                    f"Could not fetch videos from {self.channel_url}\n\n"
                    "This might be due to:\n"
                    "- Private/restricted channel\n"
                    "- Network issues\n"
                    "- yt-dlp version incompatibility\n\n"
                    "Make sure you have the latest yt-dlp installed:\n"
                    "pip install --upgrade yt-dlp"
                )
                self.reject()
                return
            
            # Populate list with all videos
            for i, video in enumerate(self.videos):
                title = video.get('title', 'Unknown')
                duration = video.get('duration', 0)
                duration_str = f"{duration//60}:{duration%60:02d}" if duration else "N/A"
                
                item_text = f"{i+1}. {title} ({duration_str}s)"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, video.get('url'))
                self.videos_list.addItem(item)
            
            self.progress_bar.setMaximum(100)
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
            
            info_text = f"✅ Found {len(self.videos)} videos from channel"
            # Update info label
            for widget in self.children():
                if isinstance(widget, QLabel) and "Loading" in widget.text():
                    widget.setText(info_text)
                    widget.setStyleSheet("font-weight: bold; color: #00ff00;")
                    break
            
            logger.info(f"Channel dialog loaded: {len(self.videos)} videos")
            
        except Exception as e:
            logger.error(f"Error fetching channel videos: {e}")
            QMessageBox.critical(self, "Error", f"Failed to fetch videos: {e}")
            self.reject()
    
    def select_all_videos(self):
        """Select all videos in the list."""
        for i in range(self.videos_list.count()):
            self.videos_list.item(i).setSelected(True)
    
    def deselect_all_videos(self):
        """Deselect all videos in the list."""
        self.videos_list.clearSelection()
    
    def on_download(self):
        """Handle download button click."""
        selected_items = self.videos_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select at least one video to download")
            return
        
        # Extract URLs from selected items
        self.selected_urls = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        
        logger.info(f"User selected {len(self.selected_urls)} videos to download")
        logger.debug(f"Selected URLs: {self.selected_urls}")
        
        # Store for later retrieval
        self.videos_selected.emit(self.selected_urls)
        self.accept()
