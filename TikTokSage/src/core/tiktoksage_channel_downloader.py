"""
TikTok Channel Downloader Module

Handles downloading all videos from a TikTok channel/user.
"""

import json
import subprocess
from pathlib import Path
from typing import List, Optional

from src.utils.tiktoksage_constants import SUBPROCESS_CREATIONFLAGS
from src.utils.tiktoksage_logger import logger


def get_channel_videos(channel_url: str, max_videos: int = 0) -> List[dict]:
    """
    Fetch all videos from a TikTok channel using yt-dlp.
    
    Args:
        channel_url: TikTok channel URL (e.g., https://www.tiktok.com/@username)
        max_videos: Maximum number of videos to fetch (0 = no limit)
    
    Returns:
        List of video info dicts with 'url', 'title', 'id' keys
    """
    videos = []
    
    try:
        # Build yt-dlp command to fetch channel videos
        cmd = [
            "yt-dlp",
            "--dump-json",
            "-j",
            "--no-warnings",
            "--extract-audio",  # Extract metadata
        ]
        
        # Add max downloads limit if specified
        if max_videos > 0:
            cmd.extend(["--max-downloads", str(max_videos)])
        
        cmd.append(channel_url)
        
        logger.info(f"Fetching channel videos with yt-dlp: {channel_url}")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=SUBPROCESS_CREATIONFLAGS,
            timeout=120
        )
        
        if result.returncode != 0:
            logger.error(f"yt-dlp error (code {result.returncode}): {result.stderr}")
            return []
        
        if not result.stdout.strip():
            logger.warning("yt-dlp returned no output")
            return []
        
        # Parse JSON output - each line is a video entry
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            
            try:
                video_data = json.loads(line)
                
                # Extract video info
                video_info = {
                    'id': video_data.get('id', ''),
                    'url': video_data.get('webpage_url', channel_url),
                    'title': video_data.get('title', 'Unknown'),
                    'duration': video_data.get('duration', 0),
                    'view_count': video_data.get('view_count', 0),
                    'upload_date': video_data.get('upload_date', ''),
                }
                
                # Only add if we have a valid URL
                if video_info['url'] and video_info['id']:
                    videos.append(video_info)
                    logger.debug(f"Found video: {video_info['title']} ({video_info['id']})")
                    
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse video JSON: {e}")
                continue
        
        logger.info(f"Successfully fetched {len(videos)} videos from channel")
        return videos
    
    except subprocess.TimeoutExpired:
        logger.error("yt-dlp timeout - channel might be too large or network issue")
        return []
    except Exception as e:
        logger.error(f"Error fetching channel videos: {e}")
        return []
