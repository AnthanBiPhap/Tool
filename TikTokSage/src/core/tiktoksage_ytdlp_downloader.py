"""
TikTok Downloader using yt-dlp

Alternative downloader using yt-dlp library for more reliable TikTok downloads.
Works around TikTok's anti-bot protection better than Playwright.
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

from src.utils.tiktoksage_logger import logger
from src.utils.tiktoksage_localization import LocalizationManager

_ = LocalizationManager.get_text


class YtDlpDownloader:
    """TikTok downloader using yt-dlp library."""
    
    def __init__(self, output_path: str = None):
        """
        Initialize yt-dlp downloader.
        
        Args:
            output_path: Directory to save videos
        """
        if yt_dlp is None:
            raise ImportError("yt-dlp is not installed. Install it with: pip install yt-dlp")
        
        self.output_path = Path(output_path) if output_path else Path.cwd()
        self.output_path.mkdir(parents=True, exist_ok=True)
    
    def get_video_info(self, url: str) -> Optional[Dict]:
        """
        Get video information using yt-dlp.
        
        Args:
            url: TikTok video URL
            
        Returns:
            Dictionary with video info or None if failed
        """
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            
            if info:
                return {
                    'title': info.get('title', 'Unknown'),
                    'author': info.get('uploader', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'description': info.get('description', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'comment_count': info.get('comment_count', 0),
                    'raw_info': info,
                }
        except Exception as e:
            logger.error(f"Error getting video info with yt-dlp: {e}")
        
        return None
    
    def download_video(self, url: str, audio_only: bool = False, 
                      progress_callback=None) -> Tuple[bool, str]:
        """
        Download TikTok video using yt-dlp.
        
        Args:
            url: TikTok video URL
            audio_only: Download only audio (M4A format)
            progress_callback: Callback function for progress updates
            
        Returns:
            Tuple of (success: bool, filepath: str)
        """
        try:
            output_template = str(self.output_path / '%(title)s.%(ext)s')
            
            ydl_opts = {
                'format': 'best[ext=mp4]' if not audio_only else 'best[ext=m4a]',
                'outtmpl': output_template,
                'quiet': False,
                'no_warnings': False,
                'progress_hooks': [self._progress_hook] if progress_callback else [],
                'socket_timeout': 30,
            }
            
            if audio_only:
                ydl_opts['format'] = 'bestaudio[ext=m4a]'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                    'preferredquality': '192',
                }]
            
            logger.info(f"Starting yt-dlp download: {url}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filepath = ydl.prepare_filename(info)
            
            logger.info(f"Download completed: {filepath}")
            return True, filepath
            
        except Exception as e:
            logger.error(f"yt-dlp download error: {e}")
            return False, str(e)
    
    def _progress_hook(self, d):
        """Progress hook for yt-dlp."""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%').strip()
            speed = d.get('_speed_str', 'N/A').strip()
            eta = d.get('_eta_str', 'N/A').strip()
            logger.info(f"Download progress: {percent} at {speed} ETA: {eta}")


def is_ytdlp_available() -> bool:
    """Check if yt-dlp is installed."""
    try:
        import yt_dlp
        return True
    except ImportError:
        return False


def install_ytdlp() -> bool:
    """
    Attempt to install yt-dlp using pip.
    
    Returns:
        True if installation successful, False otherwise
    """
    try:
        import subprocess
        import sys
        
        logger.info("Installing yt-dlp...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "yt-dlp"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            logger.info("yt-dlp installed successfully")
            return True
        else:
            logger.error(f"yt-dlp installation failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error installing yt-dlp: {e}")
        return False
