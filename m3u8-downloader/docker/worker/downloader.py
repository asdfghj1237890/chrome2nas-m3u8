"""
Segment Downloader
Multi-threaded downloader for m3u8 video segments
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Callable
import time
from pathlib import Path
import urllib3
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from ssl_adapter import create_legacy_session

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# MPEG-TS sync byte - all valid .ts files start with this
TS_SYNC_BYTE = b'\x47'
TS_PACKET_SIZE = 188

# Common file magic bytes for detecting anti-hotlink responses
JPEG_MAGIC = b'\xff\xd8\xff'
PNG_MAGIC = b'\x89PNG'
GIF_MAGIC = b'GIF8'


class SegmentDownloader:
    """Download video segments with multi-threading and retry logic"""
    
    def __init__(
        self,
        segments: List[Dict],
        output_dir: str,
        headers: Optional[Dict] = None,
        max_workers: int = 10,
        max_retries: int = 3,
        timeout: int = 30,
        encryption_key: Optional[bytes] = None,
        encryption_iv: Optional[bytes] = None
    ):
        self.segments = segments
        self.output_dir = Path(output_dir)
        self.headers = headers or {}
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.timeout = timeout
        self.encryption_key = encryption_key
        self.encryption_iv = encryption_iv
        
        self.downloaded_count = 0
        self.total_segments = len(segments)
        self.failed_segments = []
        
        # Create session with legacy SSL support
        self.session = create_legacy_session()
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _is_valid_ts_content(self, data: bytes) -> tuple[bool, str]:
        """
        Validate if the content is a valid MPEG-TS file.
        Returns (is_valid, error_reason) tuple.
        """
        if not data or len(data) < TS_PACKET_SIZE:
            return False, "Content too small"
        
        # Check for image files (anti-hotlinking protection)
        if data[:3] == JPEG_MAGIC:
            return False, "Server returned JPEG image (anti-hotlinking protection)"
        if data[:4] == PNG_MAGIC:
            return False, "Server returned PNG image (anti-hotlinking protection)"
        if data[:4] == GIF_MAGIC:
            return False, "Server returned GIF image (anti-hotlinking protection)"
        
        # Check if it starts with HTML (error page)
        if data[:5].lower() in (b'<!doc', b'<html', b'<?xml'):
            return False, "Server returned HTML error page"
        
        # Check for common error text patterns
        lower_start = data[:500].lower()
        if b'error' in lower_start or b'forbidden' in lower_start or b'denied' in lower_start:
            return False, "Server returned error response"
        
        # Check for TS sync byte at expected positions
        # TS packets are 188 bytes, sync byte should appear at 0, 188, 376, etc.
        sync_count = 0
        for i in range(0, min(len(data), TS_PACKET_SIZE * 5), TS_PACKET_SIZE):
            if data[i:i+1] == TS_SYNC_BYTE:
                sync_count += 1
        
        # If we found sync bytes at expected positions, it's likely valid
        if sync_count >= 2:
            return True, ""
        
        return False, "Invalid TS format (no sync bytes found)"
    
    def _decrypt_segment(self, data: bytes, segment_index: int) -> bytes:
        """Decrypt AES-128 encrypted segment"""
        if not self.encryption_key:
            return data
        
        # Log key info on first segment
        if segment_index == 0:
            logger.info(f"Encryption key (first 4 bytes): {self.encryption_key[:4].hex()}")
            if self.encryption_iv is not None:
                logger.info(f"Using provided IV: {self.encryption_iv.hex()}")
            else:
                logger.info("No IV provided, will use segment index")
        
        try:
            # Try multiple IV strategies
            iv_strategies = []
            
            # Strategy 1: Use provided IV if specified (HLS spec compliant)
            if self.encryption_iv is not None:
                iv_strategies.append(("provided IV", self.encryption_iv))
            
            # Strategy 2: Use segment index as IV (common non-compliant streams)
            iv_strategies.append(("segment index IV", segment_index.to_bytes(16, byteorder='big')))
            
            # Strategy 3: Use zeros IV if not already tried
            if self.encryption_iv is None or self.encryption_iv != bytes(16):
                iv_strategies.append(("zeros IV", bytes(16)))
            
            for strategy_name, iv in iv_strategies:
                cipher = AES.new(self.encryption_key, AES.MODE_CBC, iv)
                decrypted = cipher.decrypt(data)
                
                # Remove PKCS7 padding
                try:
                    decrypted = unpad(decrypted, AES.block_size)
                except ValueError:
                    # Some streams don't use proper padding
                    pass
                
                # Check if decryption produced valid TS data
                if decrypted[:1] == TS_SYNC_BYTE:
                    if segment_index < 3:  # Log first few segments
                        logger.info(f"Segment {segment_index}: Decryption successful with {strategy_name}")
                    return decrypted
            
            # None of the strategies worked
            logger.warning(f"Segment {segment_index}: All decryption strategies failed (first byte after zeros IV: {hex(decrypted[0]) if decrypted else 'empty'})")
            
            # Return the last decrypted result (with zeros IV) - let ffmpeg try to handle it
            return decrypted
            
        except Exception as e:
            logger.warning(f"Decryption failed for segment {segment_index}: {e}")
            return data  # Return original data if decryption fails
    
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
            
            # Log headers for first segment to help debug anti-hotlink issues
            if index == 0 and retry_count == 0:
                logger.info(f"Segment download headers: {self.headers}")
                logger.info(f"First segment URL: {url}")
            
            response = self.session.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                stream=False  # Don't stream, we need full content for validation
            )
            
            # Debug: Log response details on error
            if response.status_code == 474:
                logger.error(f"Segment {index} got 474 error")
                logger.error(f"Response headers: {dict(response.headers)}")
                error_content = response.text[:500] if hasattr(response, 'text') else "No content"
                logger.error(f"Error content: {error_content}")
            
            response.raise_for_status()
            
            # Get raw content
            content = response.content
            
            # Check content size
            if len(content) < 188:  # Minimum TS packet size
                raise ValueError(f"Segment too small: {len(content)} bytes")
            
            # Decrypt if encryption key is set
            if self.encryption_key:
                content = self._decrypt_segment(content, index)
            
            # Validate content is actually a TS file (not an error page)
            is_valid, error_reason = self._is_valid_ts_content(content)
            if not is_valid:
                # Check if this looks like encrypted data that we couldn't decrypt
                # In that case, still save it and let ffmpeg try to handle it
                skip_validation = os.environ.get('SKIP_TS_VALIDATION', 'false').lower() == 'true'
                
                # Always skip validation for encrypted streams where decryption produced non-image data
                if self.encryption_key and not content[:3] in (JPEG_MAGIC, PNG_MAGIC[:3], GIF_MAGIC[:3]):
                    logger.warning(f"Segment {index}: {error_reason} - saving anyway for ffmpeg to process")
                elif skip_validation:
                    logger.warning(f"Segment {index}: {error_reason} - validation skipped")
                else:
                    # Log first 200 bytes for debugging
                    preview = content[:200]
                    logger.error(f"Segment {index}: {error_reason}")
                    logger.error(f"Content preview (first 200 bytes): {preview}")
                    raise ValueError(error_reason)
            
            # Write validated content to file
            with open(output_path, 'wb') as f:
                f.write(content)
            
            logger.debug(f"Segment {index} downloaded and validated successfully ({len(content)} bytes)")
            return str(output_path)
        
        except Exception as e:
            logger.warning(f"Failed to download segment {index} (attempt {retry_count + 1}): {e}")
            
            # Retry logic
            if retry_count < self.max_retries:
                time.sleep(2 ** retry_count)  # Exponential backoff
                return self.download_segment(segment, retry_count + 1)
            else:
                logger.error(f"Segment {index} failed after {self.max_retries} attempts")
                self.failed_segments.append({'segment': segment, 'error': str(e)})
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
            try:
                for future in as_completed(future_to_segment):
                    segment = future_to_segment[future]
                    index = segment['index']
                    
                    try:
                        file_path = future.result()
                        if file_path:
                            downloaded_files[index] = file_path
                            self.downloaded_count += 1
                    
                    except Exception as e:
                        logger.error(f"Unexpected error downloading segment {index}: {e}")
                        self.failed_segments.append({'segment': segment, 'error': str(e)})
                    
                    # Call progress callback (outside try-except so callback exceptions propagate)
                    if progress_callback:
                        progress_callback(self.downloaded_count, self.total_segments)
            
            except Exception as e:
                # Callback raised an exception (e.g., too many errors detected)
                # Cancel all pending futures
                logger.warning("Download aborted, cancelling remaining tasks...")
                for future in future_to_segment:
                    future.cancel()
                # Re-raise the exception
                raise
        
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
    progress_callback: Optional[Callable[[int, int], None]] = None,
    encryption_key: Optional[bytes] = None,
    encryption_iv: Optional[bytes] = None
) -> List[str]:
    """
    Convenience function to download segments
    
    Args:
        segments: List of segment dicts
        output_dir: Directory to save segments
        headers: Optional HTTP headers
        max_workers: Number of concurrent download threads
        progress_callback: Optional callback(completed, total)
        encryption_key: Optional AES-128 encryption key
        encryption_iv: Optional AES-128 IV
    
    Returns:
        List of downloaded file paths
    """
    downloader = SegmentDownloader(
        segments=segments,
        output_dir=output_dir,
        headers=headers,
        max_workers=max_workers,
        encryption_key=encryption_key,
        encryption_iv=encryption_iv
    )
    
    return downloader.download_all(progress_callback)

