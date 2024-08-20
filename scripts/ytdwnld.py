import yt_dlp
import logging
import os
import time
from typing import Optional
import shutil

logger = logging.getLogger(__name__)

class YouTubeDownloader:
    def __init__(self, proxy_manager):
        self.proxy_manager = proxy_manager
        self.max_retries = 5
        self.retry_delay = 5  # seconds
        self.original_cookies_file = 'original_cookies.txt'
        self.working_cookies_file = 'cookies.txt'

    def download(self, youtube_url: str, output_path: str, full_video: bool) -> bool:
        for attempt in range(self.max_retries):
            proxy = self.proxy_manager.get_proxy()
            if proxy is None:
                logger.error("No proxy available. Skipping proxy for this attempt.")
                proxy = None  # Explicitly set to None to skip proxy usage
            try:
                success = self._attempt_download(youtube_url, output_path, full_video, proxy)
                if success:
                    return True
                if proxy:
                    self.proxy_manager.report_failure(proxy)
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed. Error: {str(e)}")
                if proxy:
                    self.proxy_manager.report_failure(proxy)
            time.sleep(self.retry_delay)
        
        logger.error(f"All attempts failed to download audio from {youtube_url}")
        return False

    def _attempt_download(self, youtube_url: str, output_path: str, full_video: bool, proxy: Optional[str]) -> bool:
        # Copy original cookies to working cookies file
        self._refresh_cookies()

        ydl_opts = self._get_ydl_opts(output_path, full_video, proxy)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
            
            output_file = f"{output_path}.mp3"
            if os.path.exists(output_file):
                logger.info(f"Successfully downloaded audio from {youtube_url}")
                return True
            else:
                logger.error(f"File not found after download: {output_file}")
                return False
        except Exception as e:
            logger.error(f"Error during download: {str(e)}")
            return False

    def _refresh_cookies(self):
        try:
            shutil.copy2(self.original_cookies_file, self.working_cookies_file)
            logger.info("Cookies refreshed successfully")
        except Exception as e:
            logger.error(f"Error refreshing cookies: {str(e)}")

    def _get_ydl_opts(self, output_path: str, full_video: bool, proxy: Optional[str]) -> dict:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_path,
            'ignoreerrors': True,
            'no_warnings': True,
            'cookiefile': self.working_cookies_file,  # Use the working cookies file
        }
        
        if not full_video:
            ydl_opts['postprocessor_args'] = ['-t', '15']
        
        if proxy:
            ydl_opts['proxy'] = proxy
        
        return ydl_opts

def download_mp3(youtube_url: str, output_path: str, full_video: bool) -> bool:
    from proxy_manager import proxy_manager  # Import proxy_manager here
    downloader = YouTubeDownloader(proxy_manager)
    return downloader.download(youtube_url, output_path, full_video)

# Example usage
# download_mp3('https://www.youtube.com/watch?v=UaHHVNN-z0E', 'output', full_video=False)