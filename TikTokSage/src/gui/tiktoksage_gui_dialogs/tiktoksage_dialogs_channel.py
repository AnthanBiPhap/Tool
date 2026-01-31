"""
Channel Videos Selection Dialog

Dialog for selecting videos to download from a TikTok channel.
"""

from PySide6.QtCore import Qt, Signal, QThread
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
    QFrame,
    QGroupBox,
    QScrollArea,
)

from src.gui.tiktoksage_gui_dialogs.tiktoksage_dialogs_base import BaseTikTokDialog
from src.core.tiktoksage_channel_downloader import get_channel_videos
from src.utils.tiktoksage_logger import logger


class ChannelVideosLoaderThread(QThread):
    """Background thread for loading channel videos with real-time updates."""
    
    progress_signal = Signal(str)  # Progress message
    video_found_signal = Signal(dict)  # Emitted for each video found
    progress_percent_signal = Signal(int, int)  # (current, total) - 0 total means unknown
    finished_signal = Signal(list)
    
    def __init__(self, channel_url: str, max_videos: int = 50):
        super().__init__()
        self.channel_url = channel_url
        self.max_videos = max_videos
        self.videos = []
        self._is_running = True
    
    def stop(self):
        """Stop the loading thread."""
        self._is_running = False
    
    def video_callback(self, video_info: dict):
        """Called for each video as it's fetched."""
        if not self._is_running:
            return
        self.videos.append(video_info)
        self.video_found_signal.emit(video_info)
    
    def progress_callback(self, total: int, current: int):
        """Called to update progress."""
        if not self._is_running:
            return
        self.progress_percent_signal.emit(current, total)
    
    def run(self):
        """Load videos in background with streaming."""
        try:
            self.progress_signal.emit("🔍 Connecting to TikTok...")
            
            # Get channel videos with real-time callbacks
            self.progress_signal.emit("📥 Fetching videos...")
            
            videos = get_channel_videos(
                self.channel_url, 
                max_videos=self.max_videos,
                progress_callback=self.progress_callback,
                video_callback=self.video_callback
            )
            
            # Collect any remaining videos from generator
            if hasattr(videos, '__iter__') and not isinstance(videos, list):
                for video in videos:
                    if not self._is_running:
                        break
                    self.videos.append(video)
                    self.video_found_signal.emit(video)
            else:
                self.videos = videos if videos else []
            
            logger.info(f"ChannelLoaderThread fetched {len(self.videos)} videos")
            
            if self.videos:
                self.progress_signal.emit(f"✅ Loaded {len(self.videos)} videos")
            else:
                self.progress_signal.emit("❌ No videos found")
            
            self.finished_signal.emit(self.videos)
            
        except Exception as e:
            logger.error(f"Error loading channel videos: {e}")
            self.progress_signal.emit(f"❌ Error: {str(e)}")
            self.finished_signal.emit(self.videos if hasattr(self, 'videos') else [])


class ChannelVideosDialog(BaseTikTokDialog):
    """Dialog for selecting videos from a TikTok channel."""
    
    videos_selected = Signal(list)  # Emit list of selected video URLs
    loading_progress = Signal(str)  # Emit progress messages
    loading_finished = Signal(bool, int)  # Emit success and video count
    
    def __init__(self, channel_url: str, parent=None):
        super().__init__(parent, "Select Channel Videos")
        self.channel_url = channel_url
        self.videos = []
        self.selected_urls = []  # Store selected URLs
        self._update_counter = 0  # Counter for throttling UI updates
        self.setMinimumSize(700, 500)
        
        logger.info(f"Initializing channel dialog for: {channel_url}")
        
        self.init_ui()
        self.fetch_videos_async()
        
        logger.info("Channel dialog initialized, starting async fetch")
    
    def fetch_videos_async(self):
        """Fetch videos in background thread with real-time updates."""
        max_videos = 0  # No limit - fetch all videos
        self.loading_thread = ChannelVideosLoaderThread(self.channel_url, max_videos=max_videos)
        self.loading_thread.progress_signal.connect(self.on_loading_progress)
        self.loading_thread.video_found_signal.connect(self.on_video_found, Qt.ConnectionType.QueuedConnection)
        self.loading_thread.progress_percent_signal.connect(self.on_progress_percent, Qt.ConnectionType.QueuedConnection)
        self.loading_thread.finished_signal.connect(self.on_videos_loaded)
        self.loading_thread.start()
    
    def on_video_found(self, video: dict):
        """Handle a video found in real-time."""
        if video and video.get('url'):
            self.videos.append(video)
            self._update_counter += 1
            
            # Add to list widget
            title = video.get('title', 'Unknown')
            duration = video.get('duration', 0)
            duration_str = f"{duration//60}:{duration%60:02d}" if duration else "N/A"
            
            item_text = f"{len(self.videos)}. {title} ({duration_str}s)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, video.get('url'))
            self.videos_list.addItem(item)
            
            # Only update UI every 5 videos to reduce lag
            if self._update_counter % 5 == 0:
                self.videos_list.scrollToBottom()
                self.info_label.setText(f"📥 Fetched {len(self.videos)} videos...")
                # Force process events to keep UI responsive
                from PySide6.QtWidgets import QApplication
                QApplication.processEvents()
    
    def on_progress_percent(self, current: int, total: int):
        """Handle progress percentage update."""
        if total > 0:
            percent = min(100, int((current / total) * 100))
            self.progress_bar.setMaximum(100)
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(f"{current}/{total} ({percent}%)")
        else:
            # Unknown total - show count only
            self.progress_bar.setMaximum(0)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat(f"Fetched: {current}")
    
    def on_loading_progress(self, message: str):
        """Handle loading progress updates."""
        self.loading_progress.emit(message)
        self.info_label.setText(message)
    
    def on_videos_loaded(self, videos: list):
        """Handle videos loading completed."""
        logger.info(f"Channel loading completed: {len(videos)} videos total")
        
        # Ensure videos is a list
        if videos is None:
            videos = []
        elif not isinstance(videos, list):
            videos = []
        
        self.videos = videos
        self.loading_finished.emit(len(videos) > 0, len(videos))
        
        # Finalize UI
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("100%")
        
        if videos:
            self.info_label.setText(f"✅ Found {len(videos)} videos - Select videos to download")
            logger.info(f"All {len(videos)} videos loaded successfully")
        else:
            self.info_label.setText("❌ No videos found")
            QMessageBox.warning(self, "Error", "Failed to load videos from channel")
    
    def populate_videos_list(self):
        """Populate the videos list with loaded videos."""
        if not self.videos:
            logger.warning("No videos to populate")
            return
        
        logger.info(f"Populating {len(self.videos)} videos in list widget")
        
        # Clear existing items
        self.videos_list.clear()
        
        # Add videos to list
        for i, video in enumerate(self.videos):
            title = video.get('title', 'Unknown')
            duration = video.get('duration', 0)
            duration_str = f"{duration//60}:{duration%60:02d}" if duration else "N/A"
            
            item_text = f"{i+1}. {title} ({duration_str}s)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, video.get('url'))
            self.videos_list.addItem(item)
        
        logger.info(f"Added {len(self.videos)} items to list widget")
        
        # Update progress bar
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        
        # Force UI update
        self.videos_list.update()
        self.update()
    
    def init_ui(self):
        """Initialize UI with organized sections using frames."""
        self.setMinimumSize(750, 550)
        
        # Main layout with padding
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # ========== HEADER SECTION ==========
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setStyleSheet("""
            #headerFrame {
                background-color: #252525;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(8)
        header_layout.setContentsMargins(12, 12, 12, 12)
        
        # Title
        title_label = QLabel(f"📺 Channel Videos")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4a9eff;")
        header_layout.addWidget(title_label)
        
        # Channel URL info
        channel_label = QLabel(f"Channel: {self.channel_url}")
        channel_label.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        channel_label.setWordWrap(True)
        header_layout.addWidget(channel_label)
        
        # Status label with icon
        self.info_label = QLabel("⏳ Loading videos from channel...")
        self.info_label.setStyleSheet("font-weight: bold; color: #ffffff; padding-top: 5px;")
        header_layout.addWidget(self.info_label)
        
        # Progress bar in header
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)  # Indeterminate progress
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #404040;
                border-radius: 4px;
                background-color: #1a1a1a;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4a9eff;
                border-radius: 4px;
            }
        """)
        header_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(header_frame)
        
        # ========== VIDEOS LIST SECTION ==========
        videos_group = QGroupBox("🎬 Available Videos")
        videos_group.setStyleSheet("""
            QGroupBox {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
                color: #ffffff;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                color: #4a9eff;
            }
        """)
        videos_layout = QVBoxLayout(videos_group)
        videos_layout.setContentsMargins(10, 15, 10, 10)
        
        # Videos list with improved styling
        self.videos_list = QListWidget()
        self.videos_list.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1a;
                border: 1px solid #505050;
                border-radius: 6px;
                color: #ffffff;
                padding: 5px;
                outline: none;
            }
            QListWidget::item {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px 10px;
                margin: 2px 0px;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
                border-color: #4a9eff;
            }
            QListWidget::item:selected {
                background-color: #0066cc;
                border-color: #4a9eff;
            }
            QListWidget::item:selected:hover {
                background-color: #0077dd;
            }
        """)
        self.videos_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.videos_list.setAlternatingRowColors(True)
        videos_layout.addWidget(self.videos_list)
        
        # Selection count label
        self.selection_label = QLabel("Selected: 0 videos")
        self.selection_label.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        videos_layout.addWidget(self.selection_label)
        
        # Connect selection changed
        self.videos_list.itemSelectionChanged.connect(self.on_selection_changed)
        
        main_layout.addWidget(videos_group, stretch=1)
        
        # ========== BUTTONS SECTION ==========
        buttons_frame = QFrame()
        buttons_frame.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border: 1px solid #404040;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #505050;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: 500;
                min-width: 90px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #4a9eff;
            }
            QPushButton:pressed {
                background-color: #505050;
            }
            QPushButton#downloadBtn {
                background-color: #0066cc;
                border-color: #0066cc;
                color: white;
                font-weight: bold;
            }
            QPushButton#downloadBtn:hover {
                background-color: #0077dd;
                border-color: #4a9eff;
            }
            QPushButton#downloadBtn:disabled {
                background-color: #404040;
                border-color: #505050;
                color: #888888;
            }
        """)
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setSpacing(10)
        buttons_layout.setContentsMargins(12, 12, 12, 12)
        
        # Selection buttons group
        selection_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("✓ Select All")
        select_all_btn.setToolTip("Select all videos")
        select_all_btn.clicked.connect(self.select_all_videos)
        selection_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("✗ Deselect All")
        deselect_all_btn.setToolTip("Clear all selections")
        deselect_all_btn.clicked.connect(self.deselect_all_videos)
        selection_layout.addWidget(deselect_all_btn)
        
        buttons_layout.addLayout(selection_layout)
        buttons_layout.addStretch()
        
        # Action buttons
        self.download_btn = QPushButton("⬇ Download Selected")
        self.download_btn.setObjectName("downloadBtn")
        self.download_btn.setToolTip("Download selected videos")
        self.download_btn.clicked.connect(self.on_download)
        self.download_btn.setEnabled(False)
        buttons_layout.addWidget(self.download_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setToolTip("Close this dialog")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        main_layout.addWidget(buttons_frame)
        
        self.setLayout(main_layout)
    
    def on_selection_changed(self):
        """Update selection count label."""
        count = len(self.videos_list.selectedItems())
        self.selection_label.setText(f"Selected: {count} video{'s' if count != 1 else ''}")
        self.download_btn.setEnabled(count > 0)
    
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
