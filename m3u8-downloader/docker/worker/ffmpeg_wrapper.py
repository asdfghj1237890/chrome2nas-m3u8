"""
FFmpeg Wrapper
Merge video segments into final MP4 file
"""

import logging
import subprocess
import os
from pathlib import Path
from typing import List, Optional
import shutil

logger = logging.getLogger(__name__)


class FFmpegMerger:
    """Merge video segments using FFmpeg"""
    
    def __init__(
        self,
        segment_files: List[str],
        output_file: str,
        threads: int = 4,
        concat_dir: Optional[str] = None
    ):
        self.segment_files = segment_files
        self.output_file = output_file
        self.threads = threads
        self.concat_dir = concat_dir or str(Path(output_file).parent)
        
        # Verify FFmpeg is available
        if not self._check_ffmpeg():
            raise RuntimeError("FFmpeg not found in system PATH")
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        return shutil.which('ffmpeg') is not None
    
    def _create_concat_file(self, concat_file_path: str):
        """Create concat demuxer file for FFmpeg"""
        with open(concat_file_path, 'w') as f:
            for segment_file in self.segment_files:
                # FFmpeg concat requires absolute paths with escaped characters
                abs_path = os.path.abspath(segment_file)
                # Escape special characters for FFmpeg
                escaped_path = abs_path.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
    
    def merge(self) -> bool:
        """
        Merge segments into final video file
        
        Returns:
            True if successful, False otherwise
        """
        if not self.segment_files:
            logger.error("No segment files provided")
            return False
        
        logger.info(f"Merging {len(self.segment_files)} segments into {self.output_file}")
        
        # Create temporary concat file in designated directory
        concat_file = Path(self.concat_dir) / "concat_list.txt"
        
        try:
            # Create concat file
            self._create_concat_file(str(concat_file))
            
            # FFmpeg command: use concat demuxer with copy codec (fast, no re-encoding)
            command = [
                'ffmpeg',
                '-f', 'concat',           # Use concat demuxer
                '-safe', '0',             # Allow absolute paths
                '-i', str(concat_file),   # Input concat file
                '-c', 'copy',             # Copy streams without re-encoding
                '-bsf:a', 'aac_adtstoasc', # Fix AAC audio
                '-threads', str(self.threads),
                '-y',                     # Overwrite output file
                self.output_file
            ]
            
            logger.debug(f"FFmpeg command: {' '.join(command)}")
            
            # Run FFmpeg
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            if process.returncode == 0:
                logger.info(f"Merge successful: {self.output_file}")
                
                # Verify output file exists and has size
                output_path = Path(self.output_file)
                if output_path.exists() and output_path.stat().st_size > 0:
                    file_size_mb = output_path.stat().st_size / (1024 * 1024)
                    logger.info(f"Output file size: {file_size_mb:.2f} MB")
                    return True
                else:
                    logger.error("Output file is empty or doesn't exist")
                    return False
            else:
                logger.error(f"FFmpeg failed with return code {process.returncode}")
                logger.error(f"FFmpeg stderr: {process.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg process timed out")
            return False
        
        except Exception as e:
            logger.error(f"Merge failed: {e}")
            return False
    
    def merge_with_re_encode(self) -> bool:
        """
        Merge with re-encoding (slower but more compatible)
        Use this as fallback if copy mode fails
        """
        if not self.segment_files:
            return False
        
        logger.info("Attempting merge with re-encoding (slower)")
        
        # Use same concat file location as merge()
        concat_file = Path(self.concat_dir) / "concat_list.txt"
        
        try:
            self._create_concat_file(str(concat_file))
            
            # Re-encode with H.264 and AAC
            command = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c:v', 'libx264',        # H.264 video
                '-preset', 'fast',        # Encoding speed
                '-crf', '23',             # Quality (lower = better)
                '-c:a', 'aac',            # AAC audio
                '-b:a', '128k',           # Audio bitrate
                '-threads', str(self.threads),
                '-y',
                self.output_file
            ]
            
            logger.debug(f"FFmpeg re-encode command: {' '.join(command)}")
            
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=1800  # 30 minutes for re-encoding
            )
            
            if process.returncode == 0:
                logger.info("Re-encode successful")
                return True
            else:
                logger.error(f"Re-encode failed: {process.stderr}")
                return False
        
        except Exception as e:
            logger.error(f"Re-encode failed: {e}")
            return False


def merge_segments(
    segment_files: List[str],
    output_file: str,
    threads: int = 4,
    try_re_encode: bool = True,
    concat_dir: Optional[str] = None
) -> bool:
    """
    Convenience function to merge segments
    
    Args:
        segment_files: List of segment file paths
        output_file: Output video file path
        threads: Number of FFmpeg threads
        try_re_encode: Try re-encoding if copy mode fails
        concat_dir: Directory to store temporary concat file (defaults to output_file parent)
    
    Returns:
        True if successful
    """
    merger = FFmpegMerger(segment_files, output_file, threads, concat_dir)
    concat_file = Path(concat_dir or Path(output_file).parent) / "concat_list.txt"
    
    try:
        # Try copy mode first (fast)
        success = merger.merge()
        
        # If failed and re-encode is enabled, try re-encoding
        if not success and try_re_encode:
            logger.info("Copy mode failed, attempting re-encode")
            success = merger.merge_with_re_encode()
        
        return success
    
    finally:
        # Clean up concat file
        if concat_file.exists():
            try:
                concat_file.unlink()
                logger.debug(f"Cleaned up concat file: {concat_file}")
            except Exception as e:
                logger.warning(f"Failed to cleanup concat file: {e}")

