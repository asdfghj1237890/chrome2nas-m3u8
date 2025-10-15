"""
Chrome2NAS M3U8 Downloader - Download Worker
Worker process that downloads and processes m3u8 streams
"""

import os
import sys
import time
import logging
import redis
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import signal

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/m3u8_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))

# Setup logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis setup
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Graceful shutdown handler
shutdown_flag = False

def signal_handler(sig, frame):
    global shutdown_flag
    logger.info("Shutdown signal received. Finishing current job...")
    shutdown_flag = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


class DownloadWorker:
    """Worker class for processing download jobs"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def update_job_status(self, job_id: str, status: str, progress: int = None, 
                         error_message: str = None, file_path: str = None, 
                         file_size: int = None):
        """Update job status in database"""
        try:
            updates = {"status": status}
            
            if progress is not None:
                updates["progress"] = progress
            
            if status == "downloading" and progress == 0:
                updates["started_at"] = datetime.utcnow()
            
            if status == "completed":
                updates["completed_at"] = datetime.utcnow()
                updates["progress"] = 100
            
            if error_message:
                updates["error_message"] = error_message
            
            if file_path:
                updates["file_path"] = file_path
            
            if file_size:
                updates["file_size"] = file_size
            
            # Build UPDATE query
            set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
            query = f"UPDATE jobs SET {set_clause} WHERE id = :job_id"
            updates["job_id"] = job_id
            
            self.db.execute(text(query), updates)
            self.db.commit()
            logger.info(f"Job {job_id} status updated to {status}")
        
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
            self.db.rollback()
    
    def get_job_details(self, job_id: str):
        """Get job details from database"""
        try:
            result = self.db.execute(text("""
                SELECT j.id, j.url, j.title, j.retry_count,
                       jm.referer, jm.headers, jm.source_page
                FROM jobs j
                LEFT JOIN job_metadata jm ON j.id = jm.job_id
                WHERE j.id = :job_id
            """), {"job_id": job_id})
            
            row = result.first()
            if not row:
                return None
            
            return {
                "id": str(row.id),
                "url": row.url,
                "title": row.title,
                "retry_count": row.retry_count,
                "referer": row.referer,
                "headers": json.loads(row.headers) if row.headers else {},
                "source_page": row.source_page
            }
        
        except Exception as e:
            logger.error(f"Failed to get job details: {e}")
            return None
    
    def process_job(self, job_id: str):
        """Process a download job with real m3u8 downloading"""
        logger.info(f"Processing job {job_id}")
        
        # Get job details
        job = self.get_job_details(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        # Import download modules
        from m3u8_parser import parse_m3u8
        from downloader import SegmentDownloader
        from ffmpeg_wrapper import merge_segments
        import tempfile
        import shutil
        from pathlib import Path
        
        temp_dir = None
        
        try:
            # Update status to downloading
            self.update_job_status(job_id, "downloading", progress=0)
            logger.info(f"Starting download: {job['url']}")
            
            # Step 1: Parse m3u8 playlist (5%)
            logger.info("Step 1: Parsing m3u8 playlist")
            headers = job.get('headers', {})
            if job.get('referer'):
                headers['Referer'] = job['referer']
            
            playlist_info = parse_m3u8(job['url'], headers)
            self.update_job_status(job_id, "downloading", progress=5)
            
            # Update metadata
            self.db.execute(text("""
                UPDATE job_metadata 
                SET resolution = :resolution, duration = :duration, segment_count = :segment_count
                WHERE job_id = :job_id
            """), {
                "resolution": playlist_info.get('resolution'),
                "duration": playlist_info.get('duration'),
                "segment_count": playlist_info.get('segment_count'),
                "job_id": job_id
            })
            self.db.commit()
            
            logger.info(f"Found {playlist_info['segment_count']} segments, duration: {playlist_info['duration']}s")
            
            # Step 2: Download segments (5% - 85%)
            logger.info("Step 2: Downloading segments")
            temp_dir = tempfile.mkdtemp(prefix=f"m3u8_{job_id}_")
            
            downloader = SegmentDownloader(
                segments=playlist_info['segments'],
                output_dir=temp_dir,
                headers=headers,
                max_workers=int(os.getenv('MAX_DOWNLOAD_WORKERS', 2))
            )
            
            def progress_callback(completed, total):
                # Map download progress to 5-85%
                download_progress = int(5 + (completed / total) * 80)
                self.update_job_status(job_id, "downloading", progress=download_progress)
                
                # Check if too many segments failed with 403/474 errors during download
                failed_count = len(downloader.failed_segments)
                if failed_count > 20:
                    # Count HTTP 403/474 errors
                    http_error_count = sum(
                        1 for item in downloader.failed_segments 
                        if '403' in item['error'] or '474' in item['error']
                    )
                    
                    if http_error_count > 20:
                        logger.error(f"Too many HTTP 403/474 errors detected: {http_error_count} segments failed")
                        raise Exception(f"Download aborted: {http_error_count} segments failed with HTTP 403/474 errors (URL expired or blocked)")
            
            segment_files = downloader.download_all(progress_callback)
            
            if not segment_files:
                raise Exception("No segments downloaded successfully")
            
            logger.info(f"Downloaded {len(segment_files)} segments")
            self.update_job_status(job_id, "downloading", progress=85)
            
            # Step 3: Merge with FFmpeg (85% - 95%)
            logger.info("Step 3: Merging segments with FFmpeg")
            self.update_job_status(job_id, "processing", progress=90)
            
            # Prepare output path
            safe_title = "".join(c for c in job['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_title:
                safe_title = f"video_{job_id[:8]}"
            
            # Handle file name collisions
            output_dir = Path("/downloads/completed")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            base_name = safe_title
            output_file = output_dir / f"{base_name}.mp4"
            counter = 1
            
            while output_file.exists():
                output_file = output_dir / f"{base_name} ({counter}).mp4"
                counter += 1
            
            output_file = str(output_file)
            
            # Merge segments
            success = merge_segments(
                segment_files=segment_files,
                output_file=output_file,
                threads=int(os.getenv('FFMPEG_THREADS', 4)),
                concat_dir=temp_dir
            )
            
            if not success:
                raise Exception("FFmpeg merge failed")
            
            # Get file size
            file_size = Path(output_file).stat().st_size
            
            # Step 4: Complete (95% - 100%)
            self.update_job_status(job_id, "processing", progress=95)
            
            # Cleanup temp files
            logger.info("Step 4: Cleaning up temporary files")
            downloader.cleanup()
            
            # Mark as completed
            self.update_job_status(
                job_id, 
                "completed", 
                progress=100,
                file_path=output_file,
                file_size=file_size
            )
            
            logger.info(f"Job {job_id} completed successfully: {output_file} ({file_size / 1024 / 1024:.2f} MB)")
        
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            
            error_str = str(e)
            
            # Check if error is due to 403/474 (URL expired/blocked) - do not retry
            if "403/474 errors" in error_str or "URL expired or blocked" in error_str:
                logger.warning(f"Job {job_id} failed with URL expiration/blocking error - not retrying")
                self.update_job_status(
                    job_id,
                    "failed",
                    error_message=error_str
                )
            else:
                # Update retry count for other errors
                retry_count = job.get("retry_count", 0) + 1
                
                if retry_count < MAX_RETRY_ATTEMPTS:
                    # Retry: put back in queue
                    logger.info(f"Retrying job {job_id} (attempt {retry_count})")
                    self.db.execute(text("""
                        UPDATE jobs SET retry_count = :retry_count, status = 'pending'
                        WHERE id = :job_id
                    """), {"retry_count": retry_count, "job_id": job_id})
                    self.db.commit()
                    redis_client.rpush("download_queue", job_id)
                else:
                    # Max retries reached: mark as failed
                    self.update_job_status(
                        job_id, 
                        "failed",
                        error_message=error_str
                    )
        
        finally:
            # Cleanup temp directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temp directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory: {e}")
    
    def run(self):
        """Main worker loop"""
        logger.info("Worker started and waiting for jobs...")
        
        while not shutdown_flag:
            try:
                # Blocking pop from Redis queue (timeout: 5 seconds)
                result = redis_client.blpop("download_queue", timeout=5)
                
                if result:
                    _, job_id = result
                    logger.info(f"Received job: {job_id}")
                    self.process_job(job_id)
                
            except redis.exceptions.ConnectionError as e:
                logger.error(f"Redis connection error: {e}")
                time.sleep(5)  # Wait before retrying
            
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}")
                time.sleep(1)
        
        logger.info("Worker shutting down...")
        self.db.close()


def main():
    """Main entry point"""
    logger.info("="*50)
    logger.info("Chrome2NAS M3U8 Downloader Worker")
    logger.info("Version: 2.0.0 (Phase 2 - Full Download)")
    logger.info("="*50)
    
    # Wait for database to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            logger.info("Database connection established")
            break
        except Exception as e:
            if i == max_retries - 1:
                logger.error(f"Failed to connect to database: {e}")
                sys.exit(1)
            logger.warning(f"Waiting for database... ({i+1}/{max_retries})")
            time.sleep(2)
    
    # Wait for Redis to be ready
    for i in range(max_retries):
        try:
            redis_client.ping()
            logger.info("Redis connection established")
            break
        except Exception as e:
            if i == max_retries - 1:
                logger.error(f"Failed to connect to Redis: {e}")
                sys.exit(1)
            logger.warning(f"Waiting for Redis... ({i+1}/{max_retries})")
            time.sleep(2)
    
    # Start worker
    worker = DownloadWorker()
    worker.run()


if __name__ == "__main__":
    main()

