"""
Chrome2NAS Video Downloader - API Gateway
FastAPI application for managing download jobs (M3U8 and MP4)
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, List
import os
import logging
from datetime import datetime
import redis
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import uuid

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/m3u8_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
API_KEY = os.getenv("API_KEY")

# Backward-compatible default: allow all origins unless explicitly restricted.
_allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "*").strip()
ALLOWED_ORIGINS = [o.strip() for o in _allowed_origins_raw.split(",") if o.strip()] if _allowed_origins_raw else ["*"]
ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "false").strip().lower() in ("1", "true", "yes", "y", "on")
if ALLOWED_ORIGINS == ["*"]:
    # Wildcard with credentials is not allowed by browsers and is unsafe.
    ALLOW_CREDENTIALS = False
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Setup logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Chrome2NAS Video Downloader API",
    description="API for managing video downloads (M3U8 and MP4)",
    version="1.5.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis setup
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Pydantic models
class DownloadRequest(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    referer: Optional[str] = None
    headers: Optional[dict] = None
    source_page: Optional[str] = None

    @field_validator('url')
    def validate_video_url(cls, v):
        url_str = str(v).lower()
        # Check if URL contains supported video formats
        is_valid = '.m3u8' in url_str or '.mp4' in url_str
        if not is_valid:
            raise ValueError('URL must contain .m3u8 or .mp4')
        return v

class JobResponse(BaseModel):
    id: str
    url: str
    title: Optional[str]
    status: str
    progress: int
    created_at: str
    duration: Optional[int] = None
    file_size: Optional[int] = None
    file_path: Optional[str] = None
    error_message: Optional[str] = None

class SystemStatus(BaseModel):
    status: str
    active_downloads: int
    queue_length: int
    total_jobs: int
    disk_usage_gb: Optional[float] = None

# Dependencies
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_api_key(authorization: Optional[str] = Header(None)):
    """Verify API key from Authorization header"""
    if not API_KEY or API_KEY.strip() == "" or API_KEY.strip() == "change-this-key":
        raise HTTPException(status_code=503, detail="Server not configured: API_KEY is not set")
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    # Support both "Bearer TOKEN" and just "TOKEN"
    token = authorization.replace("Bearer ", "").strip()
    
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return token

# Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Chrome2NAS M3U8 Downloader API",
        "version": "1.5.0",
        "status": "running"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        
        # Check Redis
        redis_client.ping()
        
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.post("/api/download", response_model=JobResponse)
async def submit_download(
    request: DownloadRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Submit a new download job"""
    try:
        job_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Insert job into database
        db.execute(text("""
            INSERT INTO jobs (id, url, title, status, progress, created_at)
            VALUES (:id, :url, :title, 'pending', 0, :created_at)
        """), {
            "id": job_id,
            "url": str(request.url),
            "title": request.title or "Untitled",
            "created_at": now
        })
        
        # Insert metadata
        if request.referer or request.headers or request.source_page:
            db.execute(text("""
                INSERT INTO job_metadata (job_id, referer, headers, source_page)
                VALUES (:job_id, :referer, :headers, :source_page)
            """), {
                "job_id": job_id,
                "referer": request.referer,
                "headers": json.dumps(request.headers) if request.headers else None,
                "source_page": request.source_page
            })
        
        db.commit()
        
        # Push to Redis queue
        redis_client.rpush("download_queue", job_id)
        logger.info(f"Job {job_id} created and queued")
        
        return JobResponse(
            id=job_id,
            url=str(request.url),
            title=request.title,
            status="pending",
            progress=0,
            created_at=now.isoformat()
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """List all jobs with optional status filter"""
    try:
        query = """
            SELECT j.id, j.url, j.title, j.status, j.progress, j.created_at,
                   jm.duration,
                   j.file_size, j.file_path, j.error_message
            FROM jobs j
            LEFT JOIN job_metadata jm ON j.id = jm.job_id
        """
        params = {}
        
        if status:
            query += " WHERE j.status = :status"
            params["status"] = status
        
        query += " ORDER BY j.created_at DESC LIMIT :limit"
        params["limit"] = limit
        
        result = db.execute(text(query), params)
        jobs = []
        
        for row in result:
            jobs.append(JobResponse(
                id=str(row.id),
                url=row.url,
                title=row.title,
                status=row.status,
                progress=row.progress,
                created_at=row.created_at.isoformat(),
                duration=row.duration,
                file_size=row.file_size,
                file_path=row.file_path,
                error_message=row.error_message
            ))
        
        return jobs
    
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get details of a specific job"""
    try:
        result = db.execute(text("""
            SELECT j.id, j.url, j.title, j.status, j.progress, j.created_at,
                   jm.duration,
                   j.file_size, j.file_path, j.error_message
            FROM jobs j
            LEFT JOIN job_metadata jm ON j.id = jm.job_id
            WHERE j.id = :job_id
        """), {"job_id": job_id})
        
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JobResponse(
            id=str(row.id),
            url=row.url,
            title=row.title,
            status=row.status,
            progress=row.progress,
            created_at=row.created_at.isoformat(),
            duration=row.duration,
            file_size=row.file_size,
            file_path=row.file_path,
            error_message=row.error_message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/jobs/{job_id}")
async def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Delete/cancel a job"""
    try:
        result = db.execute(text("""
            UPDATE jobs SET status = 'cancelled'
            WHERE id = :job_id AND status IN ('pending', 'downloading', 'processing')
        """), {"job_id": job_id})
        
        db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
        
        logger.info(f"Job {job_id} cancelled")
        return {"message": "Job cancelled successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status", response_model=SystemStatus)
async def get_status(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Get system status"""
    try:
        # Count active downloads
        result = db.execute(text("""
            SELECT COUNT(*) as count FROM jobs WHERE status = 'downloading'
        """))
        active_downloads = result.first().count
        
        # Count total jobs
        result = db.execute(text("SELECT COUNT(*) as count FROM jobs"))
        total_jobs = result.first().count
        
        # Get queue length
        queue_length = redis_client.llen("download_queue")
        
        return SystemStatus(
            status="healthy",
            active_downloads=active_downloads,
            queue_length=queue_length,
            total_jobs=total_jobs
        )
    
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

