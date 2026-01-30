"""
TikTok Downloader Module

Handles TikTok video downloading with support for multiple formats,
proxy settings, and cookie-based authentication.

Supports two download methods:
1. yt-dlp (preferred - more reliable)
2. TikTokApi with Playwright (fallback)
"""

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Set

import requests
from PySide6.QtCore import QObject, QThread, Signal

from src.core.tiktoksage_tiktokapi import check_tiktokapi_installed
from src.utils.tiktoksage_constants import SUBPROCESS_CREATIONFLAGS
from src.utils.tiktoksage_localization import LocalizationManager
from src.utils.tiktoksage_logger import logger

# Shorthand for localization
_ = LocalizationManager.get_text


class SignalManager(QObject):
    """Manages signals for download operations."""
    
    update_formats = Signal(list)
    update_status = Signal(str)
    update_progress = Signal(float)
    video_info_label_visible = Signal(bool)
    video_info_label_text = Signal(str)


class DownloadThread(QThread):
    """Thread for downloading TikTok videos."""
    
    progress_signal = Signal(float)
    status_signal = Signal(str)
    finished_signal = Signal()
    error_signal = Signal(str)
    file_exists_signal = Signal(str)
    update_details = Signal(str)

    def __init__(
        self,
        url: str,
        path: str,
        is_audio_only: bool = False,
        proxy_url: Optional[str] = None,
        cookie_file: Optional[str] = None,
        save_description: bool = False,
    ) -> None:
        super().__init__()
        self.url = url
        self.path = Path(path)
        self.is_audio_only = is_audio_only
        self.proxy_url = proxy_url
        self.cookie_file = cookie_file
        self.save_description = save_description
        self.paused: bool = False
        self.cancelled: bool = False
        self.process: Optional[subprocess.Popen] = None
        self.initial_subtitle_files: Set[Path] = set()
        self.subtitle_files: Optional[List[Path]] = None

    def run(self) -> None:
        """Execute the download."""
        try:
            self.status_signal.emit(_("download.preparing"))
            
            # Ensure path exists
            self.path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Starting download: {self.url}")
            self.status_signal.emit(_("download.downloading"))
            
            # Try yt-dlp first (more reliable)
            if self._try_ytdlp_download():
                return
            
            # Fallback to TikTokApi if yt-dlp fails
            logger.info("yt-dlp download failed, trying TikTokApi...")
            
            if not check_tiktokapi_installed():
                self.error_signal.emit(_("errors.tiktokapi_not_installed"))
                return
            
            # Run async code in asyncio event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._download_async())
            finally:
                loop.close()
                
        except Exception as e:
            logger.exception(f"Download error: {e}")
            self.error_signal.emit(str(e))

    def _try_ytdlp_download(self) -> bool:
        """
        Try downloading using yt-dlp.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import yt_dlp
        except ImportError:
            logger.warning("yt-dlp not installed, will try TikTokApi")
            return False
        
        try:
            logger.info("Attempting download with yt-dlp...")
            
            output_template = str(self.path / '%(title)s.%(ext)s')
            
            ydl_opts = {
                'format': 'best[ext=mp4]' if not self.is_audio_only else 'bestaudio[ext=m4a]',
                'outtmpl': output_template,
                'quiet': False,
                'no_warnings': True,
                'socket_timeout': 30,
                'no_color': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
                filepath = ydl.prepare_filename(info)
            
            logger.info(f"Download completed with yt-dlp: {filepath}")
            self.progress_signal.emit(100.0)
            self.status_signal.emit(_("download.completed"))
            self.finished_signal.emit()
            return True
            
        except Exception as e:
            logger.warning(f"yt-dlp download failed: {e}")
            return False

        except Exception as e:
            logger.exception(f"Download error: {e}")
            self.error_signal.emit(str(e))

    async def _download_async(self) -> None:
        """Async method to download video."""
        from TikTokApi import TikTokApi
        
        api = TikTokApi()
        
        # Retry logic for timeout issues
        max_retries = 2
        session_created = False
        last_error = None
        
        for attempt in range(max_retries):
            try:
                await api.create_sessions()
                session_created = True
                break
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    logger.warning(f"Session creation failed (attempt {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(2)  # Wait 2 seconds before retry
        
        # Only proceed if sessions were successfully created
        if not session_created:
            error_msg = f"Failed to connect to TikTok. Please check your internet connection or try using a VPN."
            logger.error(f"Session creation failed: {last_error}")
            self.error_signal.emit(error_msg)
            return
        
        try:
            # Get video info using the video method (NOT async, returns Video object directly)
            video_data = api.video(url=self.url)
            
            if self.cancelled:
                return
            
            if not video_data:
                self.error_signal.emit(_("errors.could_not_fetch_video_info"))
                return
            
            # Extract download URLs from video object
            download_url = None
            try:
                if hasattr(video_data, 'video') and hasattr(video_data.video, 'downloadAddr'):
                    download_url = video_data.video.downloadAddr
                elif hasattr(video_data, 'video') and hasattr(video_data.video, 'playAddr'):
                    download_url = video_data.video.playAddr
            except:
                pass
            
            if not download_url:
                self.error_signal.emit(_("errors.could_not_fetch_video_info"))
                return
            
            # Download the video
            logger.info(f"Downloading from: {download_url}")
            response = requests.get(download_url, stream=True, timeout=30)
            
            if response.status_code != 200:
                self.error_signal.emit(f"Download failed: HTTP {response.status_code}")
                return
            
            # Determine file extension and name
            ext = ".mp4" if not self.is_audio_only else ".m4a"
            try:
                title = str(video_data.desc)[:50] if hasattr(video_data, 'desc') else "video"
            except:
                title = "video"
            title = title.replace(" ", "_").replace("/", "_")
            output_file = self.path / f"{title}{ext}"
            
            # Ensure unique filename
            counter = 1
            base_file = output_file
            while output_file.exists():
                stem = base_file.stem + f"_{counter}"
                output_file = base_file.parent / (stem + base_file.suffix)
                counter += 1
            
            # Download file with progress tracking
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.cancelled:
                        output_file.unlink(missing_ok=True)
                        self.status_signal.emit(_("download.cancelled"))
                        return
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            self._update_progress(progress)
            
            # Save description if requested
            if self.save_description:
                try:
                    desc = video_data.desc if hasattr(video_data, 'desc') else ""
                    if desc:
                        desc_path = self.path / f"{title}_description.txt"
                        with open(desc_path, "w", encoding="utf-8") as f:
                            f.write(desc)
                        logger.info(f"Description saved to {desc_path}")
                except Exception as e:
                    logger.warning(f"Could not save description: {e}")
            
            self.progress_signal.emit(100.0)
            self.status_signal.emit(_("download.completed"))
            self.finished_signal.emit()
            logger.info(f"Download completed: {output_file}")
            
        except Exception as e:
            logger.exception(f"Error in _download_async: {e}")
            raise
        finally:
            try:
                await api.close_sessions()
            except Exception as e:
                logger.warning(f"Error closing API sessions: {e}")

    def _update_progress(self, progress: float) -> None:
        """Update download progress."""
        if not self.cancelled:
            self.progress_signal.emit(progress)

    def pause(self) -> None:
        """Pause the download."""
        self.paused = True
        if self.process:
            try:
                if sys.platform == "win32":
                    os.kill(self.process.pid, signal.CTRL_C_EVENT)
                else:
                    self.process.pause()
            except Exception as e:
                logger.warning(f"Error pausing download: {e}")

    def resume(self) -> None:
        """Resume the download."""
        self.paused = False
        if self.process:
            try:
                if not sys.platform == "win32":
                    self.process.resume()
            except Exception as e:
                logger.warning(f"Error resuming download: {e}")

    def cancel(self) -> None:
        """Cancel the download."""
        self.cancelled = True
        if self.process:
            self._kill_process_tree()

    def _kill_process_tree(self) -> None:
        """Kill the process and all its children."""
        if not self.process:
            return
        
        try:
            pid = self.process.pid
            
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=SUBPROCESS_CREATIONFLAGS,
                )
                logger.debug(f"Killed process tree on Windows (PID: {pid})")
            else:
                try:
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                    time.sleep(0.5)
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                logger.debug(f"Killed process group on Unix (PID: {pid})")
        except Exception as e:
            logger.warning(f"Error killing process tree: {e}")
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                    self.process.wait()
                except Exception:
                    pass


class VideoInfoThread(QThread):
    """Thread for fetching video information."""
    
    video_info_signal = Signal(dict)
    error_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, url: str, cookie_file: Optional[str] = None) -> None:
        super().__init__()
        self.url = url
        self.cookie_file = cookie_file
        self.cancelled: bool = False

    def run(self) -> None:
        """Fetch video information."""
        try:
            logger.info(f"Fetching video info: {self.url}")
            
            # Try yt-dlp first (more reliable)
            if self._try_ytdlp_video_info():
                return
            
            # Fallback to TikTokApi if yt-dlp fails
            logger.info("yt-dlp video info failed, trying TikTokApi...")
            
            if not check_tiktokapi_installed():
                self.error_signal.emit(_("errors.tiktokapi_not_installed"))
                return
            
            from TikTokApi import TikTokApi
            
            # Run async code in asyncio event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._fetch_video_async())
            finally:
                loop.close()
            
            self.finished_signal.emit()
            
        except Exception as e:
            logger.exception(f"Error fetching video info: {e}")
            self.error_signal.emit(str(e))

    def _try_ytdlp_video_info(self) -> bool:
        """
        Try fetching video info using yt-dlp.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import yt_dlp
        except ImportError:
            logger.warning("yt-dlp not installed, will try TikTokApi")
            return False
        
        try:
            logger.info("Attempting to get video info with yt-dlp...")
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'socket_timeout': 30,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
            
            if info:
                # Format the data for display
                formatted_info = {
                    "title": info.get('title', 'Unknown')[:100],
                    "author": info.get('uploader', 'Unknown'),
                    "likes": info.get('like_count', 0) or 0,
                    "comments": info.get('comment_count', 0) or 0,
                    "shares": info.get('repost_count', 0) or 0,  # Try to get share/repost count
                    "duration": info.get('duration', 0) or 0,
                    "cover": info.get('thumbnail', ''),
                    "raw_data": info,
                }
                
                logger.info(f"Video info fetched successfully with yt-dlp: {formatted_info['title']}")
                self.video_info_signal.emit(formatted_info)
                self.finished_signal.emit()
                return True
            else:
                logger.warning("yt-dlp returned empty info")
                return False
                
        except Exception as e:
            logger.warning(f"yt-dlp video info failed: {e}")
            return False


    async def _fetch_video_async(self) -> None:
        """Async method to fetch video information."""
        from TikTokApi import TikTokApi
        
        api = TikTokApi()
        
        # Retry logic for timeout issues
        max_retries = 2
        session_created = False
        last_error = None
        
        for attempt in range(max_retries):
            try:
                await api.create_sessions()
                session_created = True
                break
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    logger.warning(f"Session creation failed (attempt {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(2)  # Wait 2 seconds before retry
        
        # Only proceed if sessions were successfully created
        if not session_created:
            error_msg = f"Failed to connect to TikTok. Please check your internet connection or try using a VPN."
            logger.error(f"Session creation failed: {last_error}")
            self.error_signal.emit(error_msg)
            return
        
        try:
            # Get video information (api.video() is NOT async, returns Video object directly)
            video_info = api.video(url=self.url)
            
            if self.cancelled:
                return
            
            if video_info:
                # Extract data from Video object
                try:
                    author_id = video_info.author.uniqueId if hasattr(video_info, 'author') and hasattr(video_info.author, 'uniqueId') else "Unknown"
                except:
                    author_id = "Unknown"
                
                try:
                    likes = video_info.statistics.diggCount if hasattr(video_info, 'statistics') and hasattr(video_info.statistics, 'diggCount') else 0
                except:
                    likes = 0
                    
                try:
                    comments = video_info.statistics.commentCount if hasattr(video_info, 'statistics') and hasattr(video_info.statistics, 'commentCount') else 0
                except:
                    comments = 0
                    
                try:
                    shares = video_info.statistics.shareCount if hasattr(video_info, 'statistics') and hasattr(video_info.statistics, 'shareCount') else 0
                except:
                    shares = 0
                    
                try:
                    duration = video_info.video.duration if hasattr(video_info, 'video') and hasattr(video_info.video, 'duration') else 0
                except:
                    duration = 0
                    
                try:
                    cover = video_info.dynamicCover if hasattr(video_info, 'dynamicCover') else ""
                except:
                    cover = ""
                
                # Format the data for display
                formatted_info = {
                    "title": str(video_info.desc if hasattr(video_info, 'desc') else "Unknown")[:100],
                    "author": author_id,
                    "likes": likes,
                    "comments": comments,
                    "shares": shares,
                    "duration": duration,
                    "cover": cover,
                    "raw_data": video_info,
                }
                self.video_info_signal.emit(formatted_info)
                logger.info(f"Video info fetched successfully")
            else:
                self.error_signal.emit(_("errors.could_not_fetch_video_info"))
            
        except Exception as e:
            logger.exception(f"Error in _fetch_video_async: {e}")
            raise
        finally:
            await api.close_sessions()

    def cancel(self) -> None:
        """Cancel the operation."""
        self.cancelled = True


def get_available_formats(video_info: dict) -> List[dict]:
    """
    Extract available formats from video info.
    
    Args:
        video_info: Video information dictionary
    
    Returns:
        List of available formats
    """
    formats = []
    
    if "formats" in video_info:
        formats = video_info["formats"]
    elif "format" in video_info:
        formats = [video_info["format"]]
    
    return formats
