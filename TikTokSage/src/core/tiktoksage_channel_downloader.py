"""
TikTok Channel Downloader Module

Handles downloading all videos from a TikTok channel/user.
"""

import json
import subprocess
from pathlib import Path
from typing import List, Optional
from signal import SIGTERM

from src.utils.tiktoksage_constants import SUBPROCESS_CREATIONFLAGS
from src.utils.tiktoksage_logger import logger


def get_channel_videos(channel_url: str, max_videos: int = 0, progress_callback=None, video_callback=None):
    """
    Fetch all videos from a TikTok channel using yt-dlp with fallback options.
    Streams videos in real-time as they are fetched.
    
    Args:
        channel_url: TikTok channel URL (e.g., https://www.tiktok.com/@username)
        max_videos: Maximum number of videos to fetch (0 = no limit)
        progress_callback: Callable(total_videos, current_progress) for progress updates
        video_callback: Callable(video_info) called for each video as it's fetched
    
    Yields:
        Video info dicts with 'url', 'title', 'id' keys (if video_callback not provided)
    
    Returns:
        List of all video info dicts
    """
    videos = []
    videos_yielded = 0
    
    try:
        # Try different yt-dlp approaches for TikTok
        approaches = [
            # Approach 1: Standard with user-agent
            [
                "yt-dlp",
                "--dump-json",
                "-j",
                "--no-warnings",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--extract-audio",
            ],
            # Approach 2: Mobile user-agent
            [
                "yt-dlp",
                "--dump-json", 
                "-j",
                "--no-warnings",
                "--user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
                "--extract-audio",
            ],
            # Approach 3: With additional headers
            [
                "yt-dlp",
                "--dump-json",
                "-j", 
                "--no-warnings",
                "--add-header", "Referer:https://www.tiktok.com/",
                "--add-header", "Accept-Language:en-US,en;q=0.9",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "--extract-audio",
            ],
            # Approach 4: Without extract-audio (just metadata)
            [
                "yt-dlp",
                "--dump-json",
                "-j",
                "--no-warnings",
                "--flat-playlist",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ],
            # Approach 5: With cookies and lazy extraction
            [
                "yt-dlp",
                "--dump-json",
                "-j",
                "--no-warnings",
                "--lazy-playlist",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ]
        ]
        
        for approach_idx, base_cmd in enumerate(approaches):
            videos = []
            videos_yielded = 0
            
            try:
                cmd = base_cmd.copy()
                
                # Add max downloads limit if specified
                if max_videos > 0:
                    cmd.extend(["--max-downloads", str(max_videos)])
                
                cmd.append(channel_url)
                
                logger.info(f"Trying approach {approach_idx + 1} for channel videos: {channel_url}")
                logger.debug(f"Command: {' '.join(cmd)}")
                
                # Use Popen to stream output in real-time
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=SUBPROCESS_CREATIONFLAGS,
                    bufsize=1,  # Line buffered
                    universal_newlines=True
                )
                
                logger.info(f"Streaming videos from approach {approach_idx + 1}...")
                
                # Stream and parse output line by line
                for line in process.stdout:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        video_data = json.loads(line)
                        if video_data:
                            video_info = {
                                'url': video_data.get('webpage_url', video_data.get('url', '')),
                                'title': video_data.get('title', 'Unknown'),
                                'id': video_data.get('id', ''),
                                'duration': video_data.get('duration', 0),
                                'thumbnail': video_data.get('thumbnail', '')
                            }
                            
                            if video_info['url']:
                                videos.append(video_info)
                                videos_yielded += 1
                                
                                # Call video callback if provided
                                if video_callback:
                                    video_callback(video_info)
                                else:
                                    yield video_info
                                
                                # Update progress
                                if progress_callback:
                                    progress_callback(max_videos if max_videos > 0 else 0, videos_yielded)
                                
                                # Check max videos limit
                                if max_videos > 0 and videos_yielded >= max_videos:
                                    process.terminate()
                                    break
                                    
                    except json.JSONDecodeError:
                        continue
                
                # Wait for process to complete with longer timeout for many videos
                try:
                    process.wait(timeout=300)  # 5 minutes timeout for large channels
                except subprocess.TimeoutExpired:
                    logger.warning("Process timeout - terminating")
                    process.terminate()
                    process.wait()
                
                # Check stderr for any issues but don't fail if we got videos
                stderr_output = process.stderr.read() if process.stderr else ""
                
                if stderr_output:
                    logger.debug(f"Approach {approach_idx + 1} stderr: {stderr_output[:500]}")
                
                if videos:
                    logger.info(f"Successfully fetched {len(videos)} videos using approach {approach_idx + 1}")
                    return videos
                elif stderr_output:
                    logger.warning(f"Approach {approach_idx + 1} failed: {stderr_output[:200]}")
                else:
                    logger.warning(f"Approach {approach_idx + 1} failed or returned no videos")
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"Approach {approach_idx + 1} timed out")
                if videos:
                    return videos
                continue
            except Exception as e:
                logger.warning(f"Approach {approach_idx + 1} error: {e}")
                if videos:
                    return videos
                continue
        
        if not videos:
            logger.error("All approaches failed to fetch channel videos")
            return []
            
        return videos
            
    except Exception as e:
        logger.error(f"Error in get_channel_videos: {e}")
        return []
