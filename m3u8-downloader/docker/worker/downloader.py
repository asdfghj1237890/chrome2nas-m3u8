"""
Segment Downloader
Multi-threaded downloader for m3u8 video segments
"""

import logging
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Callable
import time
from pathlib import Path
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class SegmentDownloader:
    """Download video segments with multi-threading and retry logic"""
    
    def __init__(
        self,
        segments: List[Dict],
        output_dir: str,
        headers: Optional[Dict] = None,
        max_workers: int = 10,
        max_retries: int = 3,
        timeout: int = 30
    ):
        self.segments = segments
        self.output_dir = Path(output_dir)
        self.headers = headers or {}
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.timeout = timeout
        
        self.downloaded_count = 0
        self.total_segments = len(segments)
        self.failed_segments = []
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def download_segment(
        self, 
        segment: Dict, 
        retry_count: int = 0
    ) -> Optional[str]:
        """
        Download a single segment
        
        Args:
            segment: Segment info dict with 'url', 'index'
            retry_count: Current retry attempt
        
        Returns:
            Path to downloaded file or None if failed
        """
        url = segment['url']
        index = segment['index']
        output_path = self.output_dir / f"segment_{index:05d}.ts"
        
        try:
            logger.debug(f"Downloading segment {index}: {url}")
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                stream=True,
                verify=False
            )
            response.raise_for_status()
            
            # Write to file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.debug(f"Segment {index} downloaded successfully")
            return str(output_path)
        
        except Exception as e:
            logger.warning(f"Failed to download segment {index} (attempt {retry_count + 1}): {e}")
            
            # Retry logic
            if retry_count < self.max_retries:
                time.sleep(2 ** retry_count)  # Exponential backoff
                return self.download_segment(segment, retry_count + 1)
            else:
                logger.error(f"Segment {index} failed after {self.max_retries} attempts")
                self.failed_segments.append(segment)
                return None
    
    def download_all(
        self, 
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[str]:
        """
        Download all segments with multi-threading
        
        Args:
            progress_callback: Optional callback function(completed, total)
        
        Returns:
            List of downloaded file paths
        """
        logger.info(f"Starting download of {self.total_segments} segments with {self.max_workers} workers")
        
        downloaded_files = [None] * self.total_segments
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all download tasks
            future_to_segment = {
                executor.submit(self.download_segment, segment): segment
                for segment in self.segments
            }
            
            # Process completed downloads
            for future in as_completed(future_to_segment):
                segment = future_to_segment[future]
                index = segment['index']
                
                try:
                    file_path = future.result()
                    if file_path:
                        downloaded_files[index] = file_path
                        self.downloaded_count += 1
                    
                    # Call progress callback
                    if progress_callback:
                        progress_callback(self.downloaded_count, self.total_segments)
                
                except Exception as e:
                    logger.error(f"Unexpected error downloading segment {index}: {e}")
                    self.failed_segments.append(segment)
        
        # Filter out None values (failed downloads)
        successful_files = [f for f in downloaded_files if f is not None]
        
        logger.info(f"Download complete: {len(successful_files)}/{self.total_segments} segments successful")
        
        if self.failed_segments:
            logger.warning(f"Failed segments: {len(self.failed_segments)}")
        
        return successful_files
    
    def get_progress(self) -> Dict:
        """Get download progress information"""
        return {
            'downloaded': self.downloaded_count,
            'total': self.total_segments,
            'percentage': int((self.downloaded_count / self.total_segments) * 100),
            'failed': len(self.failed_segments)
        }
    
    def cleanup(self):
        """Remove downloaded segment files"""
        try:
            logger.info("Cleaning up segment files")
            for file in self.output_dir.glob("segment_*.ts"):
                file.unlink()
            
            # Try to remove directory if empty
            try:
                self.output_dir.rmdir()
            except OSError:
                pass  # Directory not empty or doesn't exist
        
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")


def download_segments(
    segments: List[Dict],
    output_dir: str,
    headers: Optional[Dict] = None,
    max_workers: int = 10,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[str]:
    """
    Convenience function to download segments
    
    Args:
        segments: List of segment dicts
        output_dir: Directory to save segments
        headers: Optional HTTP headers
        max_workers: Number of concurrent download threads
        progress_callback: Optional callback(completed, total)
    
    Returns:
        List of downloaded file paths
    """
    downloader = SegmentDownloader(
        segments=segments,
        output_dir=output_dir,
        headers=headers,
        max_workers=max_workers
    )
    
    return downloader.download_all(progress_callback)

