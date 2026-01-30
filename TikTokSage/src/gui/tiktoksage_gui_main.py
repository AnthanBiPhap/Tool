"""
TikTokSage Main GUI Application

Main application window for TikTokSage TikTok video downloader.
"""

import threading
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStyle,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QLabel,
)

from src import __version__ as APP_VERSION
from src.core.tiktoksage_downloader import DownloadThread, SignalManager, VideoInfoThread
from src.core.tiktoksage_utils import (
    check_ffmpeg,
    load_saved_path,
    save_path,
    validate_tiktok_url,
)
from src.core.tiktoksage_tiktokapi import check_tiktokapi_binary, setup_tiktokapi
from src.utils.tiktoksage_constants import ICON_PATH, SUBPROCESS_CREATIONFLAGS
from src.utils.tiktoksage_logger import logger
from src.utils.tiktoksage_config_manager import ConfigManager
from src.utils.tiktoksage_localization import LocalizationManager, _
from src.utils.tiktoksage_history_manager import HistoryManager
from src.gui.tiktoksage_gui_dialogs import HistoryDialog


class TikTokSageApp(QMainWindow):
    """Main application window."""
    
    def __init__(self) -> None:
        super().__init__()

        # Initialize localization system
        saved_language = ConfigManager.get("language") or "en"
        LocalizationManager.initialize(saved_language)

        # Check for TikTokApi
        if not check_tiktokapi_binary():
            self.show_tiktokapi_setup_dialog()

        self.version = APP_VERSION
        load_saved_path(self)
        
        # Load custom icon (silently fail if not found)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        else:
            # Use default icon without warning
            self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))

        self.signals = SignalManager()
        self.download_paused = False
        self.current_download = None
        self.download_cancelled = False
        self.is_analyzing = False
        self.save_description = False
        self.thumbnail_url = None
        self.video_info = None
        self.video_url = ""
        
        # Initialize proxy settings from config
        self.proxy_url = ConfigManager.get("proxy_url")
        
        self.init_ui()
        self.setup_styles()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle(f"TikTokSage v{self.version}")
        self.setGeometry(100, 100, 900, 700)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout()

        # URL Input Section
        url_layout = QHBoxLayout()
        url_label = QLabel("Video URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.tiktok.com/@user/video/...")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        main_layout.addLayout(url_layout)

        # Download Path Section
        path_layout = QHBoxLayout()
        path_label = QLabel("Download Path:")
        self.path_input = QLineEdit()
        self.path_input.setText(load_saved_path())
        path_btn = QPushButton("Browse")
        path_btn.clicked.connect(self.browse_download_path)
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_btn)
        main_layout.addLayout(path_layout)

        # Options Section
        options_layout = QHBoxLayout()
        
        self.audio_only_checkbox = QCheckBox("Audio Only")
        options_layout.addWidget(self.audio_only_checkbox)
        
        self.save_description_checkbox = QCheckBox("Save Description")
        options_layout.addWidget(self.save_description_checkbox)
        
        main_layout.addLayout(options_layout)

        # Video Info Display
        info_label = QLabel("Video Information:")
        main_layout.addWidget(info_label)
        
        # Create horizontal layout for thumbnail + info
        info_container = QHBoxLayout()
        
        # Thumbnail display (match info area size for balanced layout)
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setMinimumSize(420, 260)
        self.thumbnail_label.setMaximumSize(420, 260)
        self.thumbnail_label.setStyleSheet("border: 1px solid #555; background-color: #222; color: #fff;")
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setText("No Image")
        info_container.addWidget(self.thumbnail_label)
        
        # Video info text (vertical, larger font)
        self.video_info_display = QTextEdit()
        self.video_info_display.setReadOnly(True)
        # Make the info area larger for readability while keeping text size unchanged
        self.video_info_display.setMinimumHeight(260)
        self.video_info_display.setMinimumWidth(420)
        # Increase padding but keep font size the same
        self.video_info_display.setStyleSheet(
            "QTextEdit { font-size: 14px; padding: 10px; background-color: #1b2021; color: #fff; }"
        )
        info_container.addWidget(self.video_info_display)
        
        main_layout.addLayout(info_container)

        # Progress Section
        progress_label = QLabel("Progress:")
        main_layout.addWidget(progress_label)
        
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)

        # Button Section
        button_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.clicked.connect(self.analyze_video)
        button_layout.addWidget(self.analyze_btn)
        
        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_btn)
        
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_download)
        button_layout.addWidget(self.pause_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_download)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)

        # History Button (hidden)
        # history_btn = QPushButton("History")
        # history_btn.clicked.connect(self.show_history)
        # main_layout.addWidget(history_btn)

        main_layout.addStretch()
        central_widget.setLayout(main_layout)

        # Toast label for transient, no-icon notifications
        self._toast_label = QLabel(self)
        self._toast_label.setVisible(False)
        self._toast_label.setStyleSheet(
            "QLabel { background-color: #2b2f31; color: #ffffff; padding: 10px 14px; border-radius: 8px; }")
        self._toast_label.setWindowFlag(Qt.ToolTip)

    def setup_styles(self) -> None:
        """Setup application styles."""
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #15181b;
            }
            QWidget {
                background-color: #15181b;
                color: #ffffff;
            }
            QLineEdit {
                padding: 5px 15px;
                border: 2px solid #2a2d2e;
                border-radius: 6px;
                background-color: #1b2021;
                color: #ffffff;
            }
            QPushButton {
                padding: 8px 16px;
                background-color: #1da1f2;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1a91da;
            }
            QPushButton:pressed {
                background-color: #1680b8;
            }
            QPushButton:disabled {
                background-color: #666666;
            }
            QProgressBar {
                border: 2px solid #2a2d2e;
                border-radius: 6px;
                background-color: #1b2021;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #1da1f2;
                border-radius: 4px;
            }
            QTextEdit {
                border: 2px solid #2a2d2e;
                border-radius: 6px;
                background-color: #1b2021;
                color: #ffffff;
            }
            """
        )

    def browse_download_path(self) -> None:
        """Browse for download directory."""
        path = QFileDialog.getExistingDirectory(self, "Select Download Directory")
        if path:
            self.path_input.setText(path)
            save_path(path)

    def analyze_video(self) -> None:
        """Analyze the video to get information."""
        url = self.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, _("dialogs.error"), _("errors.empty_url"))
            return
        
        if not validate_tiktok_url(url):
            QMessageBox.warning(self, _("dialogs.error"), _("errors.invalid_tiktok_url"))
            return
        
        self.is_analyzing = True
        self.analyze_btn.setEnabled(False)
        self.status_label.setText(_("download.analyzing"))
        
        self.info_thread = VideoInfoThread(url)
        self.info_thread.video_info_signal.connect(self.on_video_info_received)
        self.info_thread.error_signal.connect(self.on_video_info_error)
        self.info_thread.finished_signal.connect(self.on_video_info_finished)
        self.info_thread.start()

    @Slot(dict)
    def on_video_info_received(self, video_info: dict) -> None:
        """Handle video information received."""
        self.video_info = video_info
        
        # Display thumbnail if available (try several keys)
        thumbnail_url = (
            video_info.get('cover')
            or video_info.get('thumbnail')
            or (video_info.get('raw_data') or {}).get('thumbnail')
            or ''
        )
        logger.info(f"Thumbnail URL: {thumbnail_url}")
        if thumbnail_url:
            try:
                import requests
                # Download thumbnail
                response = requests.get(thumbnail_url, timeout=8)
                logger.info(f"Thumbnail HTTP status: {getattr(response, 'status_code', None)}")
                if response.status_code == 200 and response.content:
                    pixmap = QPixmap()
                    pixmap.loadFromData(response.content)

                    # Scale to fit label (match thumbnail_label size)
                    scaled_pixmap = pixmap.scaled(420, 260, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.thumbnail_label.setPixmap(scaled_pixmap)
                else:
                    logger.debug("Thumbnail response invalid or empty")
                    self.thumbnail_label.setText("No Image")
            except Exception as e:
                logger.debug(f"Could not load thumbnail: {e}")
                self.thumbnail_label.setText("No Image")
        else:
            self.thumbnail_label.setText("No Image")
        
        # Display video info (vertical format for readability)
        duration = video_info.get('duration', 0)
        duration_text = f"{int(duration // 60)}:{int(duration % 60):02d}" if duration > 0 else "N/A"
        
        title = video_info.get('title', 'Unknown')[:60]
        author = video_info.get('author', 'Unknown')
        likes = video_info.get('likes', 0)
        comments = video_info.get('comments', 0)
        shares = video_info.get('shares', 0)

        # Multi-line format (vertical) — put each stat on its own line for clarity
        info_text = f"""
    <div>
      <div style='font-size:14pt; font-weight:600;'>{title}</div>
      <div style='color:#aaaaaa; margin-bottom:8px;'>By: {author}</div>
    <div style='line-height:1.6;'>
        ❤️ <b>Likes:</b> {likes:,}<br>
        💬 <b>Comments:</b> {comments:,}<br>
        ♻️ <b>Shares:</b> {shares:,}<br>
        ⏱ <b>Duration:</b> {duration_text}
    </div>
</div>
"""
        
        self.video_info_display.setText(info_text)
        self.download_btn.setEnabled(True)

    @Slot(str)
    def on_video_info_error(self, error: str) -> None:
        """Handle video info error."""
        QMessageBox.critical(self, _("dialogs.error"), f"Error: {error}")

    @Slot()
    def on_video_info_finished(self) -> None:
        """Handle video info finished."""
        self.is_analyzing = False
        self.analyze_btn.setEnabled(True)
        if not self.video_info:
            self.status_label.setText(_("download.ready"))

    def start_download(self) -> None:
        """Start downloading the video."""
        url = self.url_input.text().strip()
        path = self.path_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, _("dialogs.error"), _("errors.empty_url"))
            return
        
        if not validate_tiktok_url(url):
            QMessageBox.warning(self, _("dialogs.error"), _("errors.invalid_tiktok_url"))
            return
        
        if not path:
            QMessageBox.warning(self, _("dialogs.error"), _("errors.empty_path"))
            return
        
        self.save_description = self.save_description_checkbox.isChecked()
        is_audio_only = self.audio_only_checkbox.isChecked()
        
        # Create and start download thread
        self.current_download = DownloadThread(
            url=url,
            path=path,
            is_audio_only=is_audio_only,
            proxy_url=self.proxy_url,
            save_description=self.save_description,
        )
        
        self.current_download.progress_signal.connect(self.update_progress)
        self.current_download.status_signal.connect(self.update_status)
        self.current_download.finished_signal.connect(self.on_download_finished)
        self.current_download.error_signal.connect(self.on_download_error)
        
        self.current_download.start()
        
        self.download_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)

    @Slot(float)
    def update_progress(self, progress: float) -> None:
        """Update progress bar."""
        self.progress_bar.setValue(int(progress))

    @Slot(str)
    def update_status(self, status: str) -> None:
        """Update status label."""
        self.status_label.setText(status)

    def pause_download(self) -> None:
        """Pause the download."""
        if self.current_download:
            self.current_download.pause()
            self.pause_btn.setText("Resume")
            self.pause_btn.clicked.disconnect()
            self.pause_btn.clicked.connect(self.resume_download)
            self.download_paused = True

    def resume_download(self) -> None:
        """Resume the download."""
        if self.current_download:
            self.current_download.resume()
            self.pause_btn.setText("Pause")
            self.pause_btn.clicked.disconnect()
            self.pause_btn.clicked.connect(self.pause_download)
            self.download_paused = False

    def cancel_download(self) -> None:
        """Cancel the download."""
        if self.current_download:
            self.current_download.cancel()
            self.on_download_cancelled()

    def on_download_cancelled(self) -> None:
        """Handle download cancelled."""
        self.status_label.setText(_("download.cancelled"))
        self.reset_download_controls()

    @Slot()
    def on_download_finished(self) -> None:
        """Handle download finished."""
        # Add to history
        if self.video_info:
            HistoryManager.add_entry(
                title=self.video_info.get("title", "Unknown"),
                url=self.url_input.text(),
                thumbnail_url=self.video_info.get("cover", None),
                is_audio_only=self.audio_only_checkbox.isChecked(),
            )
        
        # Show transient in-app toast (no system icon)
        self.show_toast(_("download.completed"))
        self.reset_download_controls()

    def show_toast(self, text: str, timeout: int = 2500) -> None:
        """Show a small transient toast message inside the app without an icon."""
        if not hasattr(self, "_toast_label") or self._toast_label is None:
            self._toast_label = QLabel(self)
        lbl = self._toast_label
        lbl.setText(text)
        lbl.adjustSize()
        # Position bottom-right inside the main window with margin
        margin_x = 20
        margin_y = 40
        x = max(10, self.width() - lbl.width() - margin_x)
        y = max(10, self.height() - lbl.height() - margin_y)
        lbl.move(x, y)
        lbl.setVisible(True)
        QTimer.singleShot(timeout, lambda: lbl.setVisible(False))

    @Slot(str)
    def on_download_error(self, error: str) -> None:
        """Handle download error."""
        QMessageBox.critical(self, _("dialogs.error"), f"Download Error: {error}")
        self.reset_download_controls()

    def reset_download_controls(self) -> None:
        """Reset download control states."""
        self.download_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self.pause_btn.clicked.disconnect()
        self.pause_btn.clicked.connect(self.pause_download)
        self.download_paused = False
        self.current_download = None

    def show_history(self) -> None:
        """Show download history."""
        dialog = HistoryDialog(self)
        dialog.exec()

    def show_tiktokapi_setup_dialog(self) -> None:
        """Show TikTokApi setup dialog."""
        result = setup_tiktokapi()
        if result != "ok":
            QMessageBox.critical(
                self,
                _("dialogs.error"),
                "TikTokApi is required to use TikTokSage.\nPlease install it and restart the application.",
            )
            QApplication.quit()

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        if self.current_download and self.current_download.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Download in progress. Are you sure you want to exit?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            self.current_download.cancel()
            self.current_download.wait()
        
        event.accept()
