# System Architecture

## Overview

This document provides detailed architecture diagrams and explanations for the Chrome2NAS M3U8 Downloader system.

---

## 1. High-Level System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                         USER'S COMPUTER                         │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Chrome Browser                          │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────┐     │  │
│  │  │  Website (Streaming Service)                    │     │  │
│  │  │  └─→ Serves m3u8 playlist                       │     │  │
│  │  └─────────────────────────────────────────────────┘     │  │
│  │                         ↑                                 │  │
│  │                         │ User browses                    │  │
│  │                         ↓                                 │  │
│  │  ┌─────────────────────────────────────────────────┐     │  │
│  │  │  Chrome2NAS Extension                           │     │  │
│  │  │  • Detects m3u8 URLs                           │     │  │
│  │  │  • Displays popup UI                           │     │  │
│  │  │  • Sends to NAS API                            │     │  │
│  │  └─────────────────────────────────────────────────┘     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         ↓                                       │
│                    HTTPS Request                                │
│                  {url, headers, metadata}                       │
│                         ↓                                       │
└───────────────────────────────────────────────────────────────┘
                          │
                          ↓
┌────────────────────────────────────────────────────────────────┐
│                        NAS DEVICE                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Docker Compose Network                       │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────┐     │  │
│  │  │  nginx (Reverse Proxy)                          │     │  │
│  │  │  • SSL termination                              │     │  │
│  │  │  • Rate limiting                                │     │  │
│  │  │  Port: 443 → 8000                              │     │  │
│  │  └──────────────────┬──────────────────────────────┘     │  │
│  │                     ↓                                     │  │
│  │  ┌─────────────────────────────────────────────────┐     │  │
│  │  │  API Gateway (FastAPI)                          │     │  │
│  │  │  • Authentication                               │     │  │
│  │  │  • Job management                               │     │  │
│  │  │  • Status tracking                              │     │  │
│  │  │  Port: 8000                                     │     │  │
│  │  └──────────────┬──────────────┬───────────────────┘     │  │
│  │                 ↓              ↓                          │  │
│  │   ┌─────────────────┐  ┌─────────────────┐              │  │
│  │   │  PostgreSQL     │  │  Redis          │              │  │
│  │   │  • Job data     │  │  • Job queue    │              │  │
│  │   │  • Metadata     │  │  • Pub/Sub      │              │  │
│  │   │  Port: 5432     │  │  Port: 6379     │              │  │
│  │   └────────┬────────┘  └────────┬────────┘              │  │
│  │            ↓                     ↓                        │  │
│  │            └──────────┬──────────┘                        │  │
│  │                       ↓                                   │  │
│  │  ┌─────────────────────────────────────────────────┐     │  │
│  │  │  Download Worker (Python)                       │     │  │
│  │  │  • Poll Redis queue                             │     │  │
│  │  │  • Parse m3u8                                   │     │  │
│  │  │  • Download segments                            │     │  │
│  │  │  • Merge with FFmpeg                            │     │  │
│  │  │  • Update database                              │     │  │
│  │  └──────────────────┬──────────────────────────────┘     │  │
│  │                     ↓                                     │  │
│  └─────────────────────┼─────────────────────────────────────┘
│                        ↓                                       │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  NAS Storage Volume                                 │     │
│  │  /volume1/downloads/m3u8/                          │     │
│  │  ├── completed/                                     │     │
│  │  ├── processing/                                    │     │
│  │  └── failed/                                        │     │
│  └─────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow - Download Job Lifecycle

```
┌─────────────┐
│   Chrome    │
│  Extension  │
└──────┬──────┘
       │
       │ 1. User clicks "Send to NAS"
       │
       ↓
┌─────────────────────────────────────────────────────────┐
│ POST /api/download                                      │
│ {                                                       │
│   "url": "https://example.com/video.m3u8",            │
│   "title": "Video Title",                             │
│   "referer": "https://example.com",                   │
│   "headers": {...}                                     │
│ }                                                       │
└─────────────────────────┬───────────────────────────────┘
                          │
                          │ 2. API validates and creates job
                          │
                          ↓
                    ┌──────────┐
                    │PostgreSQL│
                    │ INSERT   │
                    │ job row  │
                    │status:   │
                    │'pending' │
                    └─────┬────┘
                          │
                          │ 3. Push to queue
                          │
                          ↓
                    ┌──────────┐
                    │  Redis   │
                    │  Queue   │
                    │ RPUSH    │
                    │ job_id   │
                    └─────┬────┘
                          │
                          │ 4. Worker polls queue
                          │
                          ↓
         ┌─────────────────────────────────────┐
         │      Download Worker Process         │
         ├──────────────────────────────────────┤
         │                                      │
         │  Step 1: Update status               │
         │  └─→ status = 'downloading'          │
         │      progress = 0%                   │
         │                                      │
         │  Step 2: Parse M3U8                  │
         │  └─→ GET master playlist             │
         │      └─→ Select quality              │
         │          └─→ Parse media playlist    │
         │              └─→ Extract segments    │
         │                                      │
         │  Step 3: Download Segments           │
         │  ┌────────────────────────┐          │
         │  │ Segment 1 │ Thread 1   │          │
         │  │ Segment 2 │ Thread 2   │          │
         │  │ ...       │ ...        │          │
         │  │ Segment N │ Thread 10  │          │
         │  └────────────────────────┘          │
         │  └─→ Update progress: 0-90%          │
         │                                      │
         │  Step 4: Merge with FFmpeg           │
         │  └─→ ffmpeg -i playlist -c copy out  │
         │      └─→ Update progress: 90-99%     │
         │                                      │
         │  Step 5: Finalize                    │
         │  └─→ Move to /completed/             │
         │      └─→ Update status='completed'   │
         │          └─→ progress = 100%         │
         │                                      │
         └───────────────┬──────────────────────┘
                         │
                         │ 5. Notify completion
                         │
                         ↓
                  ┌─────────────┐
                  │ Extension   │
                  │ Notification│
                  │ "Download   │
                  │  Complete!" │
                  └─────────────┘
```

---

## 3. Component Interaction Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    Extension Lifecycle                        │
└──────────────────────────────────────────────────────────────┘

1. Background Script (Service Worker)
   ├─→ Listen: webRequest.onBeforeRequest
   │   └─→ Filter: *.m3u8
   │       └─→ Store: detectedUrls[]
   │           └─→ Update: Badge count
   │
   ├─→ Listen: contextMenus.onClicked
   │   └─→ Action: sendToNAS(url)
   │       └─→ API: POST /api/download
   │
   └─→ Listen: chrome.alarms
       └─→ Action: pollJobStatus()
           └─→ API: GET /api/jobs

2. Popup UI
   ├─→ Display: Detected URLs
   ├─→ Display: Active downloads
   │   └─→ Progress bars
   └─→ Button: Send to NAS

3. Settings Page
   ├─→ Input: NAS endpoint
   ├─→ Input: API key
   └─→ Button: Test connection

┌──────────────────────────────────────────────────────────────┐
│                     API Gateway Services                      │
└──────────────────────────────────────────────────────────────┘

FastAPI Application
├─→ Middleware
│   ├─→ CORS (allow Chrome extension)
│   ├─→ Rate limiting (10 req/min)
│   └─→ Authentication (API key)
│
├─→ Routers
│   ├─→ /api/download
│   │   ├─→ Validate URL
│   │   ├─→ Generate job_id
│   │   ├─→ INSERT into PostgreSQL
│   │   ├─→ RPUSH to Redis
│   │   └─→ Return 201 + job_id
│   │
│   ├─→ /api/jobs
│   │   ├─→ SELECT from PostgreSQL
│   │   └─→ Return paginated list
│   │
│   ├─→ /api/jobs/{id}
│   │   ├─→ SELECT WHERE id
│   │   └─→ Return job details
│   │
│   └─→ /api/status
│       ├─→ COUNT(*) WHERE status='downloading'
│       ├─→ LLEN redis queue
│       ├─→ Disk usage
│       └─→ Return system status
│
└─→ Error Handlers
    ├─→ 401: Invalid API key
    ├─→ 404: Job not found
    └─→ 500: Internal error

┌──────────────────────────────────────────────────────────────┐
│                      Worker Process                           │
└──────────────────────────────────────────────────────────────┘

Main Loop
├─→ while True:
    ├─→ job_id = BLPOP redis queue (blocking)
    ├─→ job = SELECT from PostgreSQL
    ├─→ try:
    │   ├─→ download_video(job)
    │   └─→ UPDATE status='completed'
    ├─→ except Exception as e:
    │   ├─→ retry_count += 1
    │   ├─→ if retry_count < 3:
    │   │   └─→ RPUSH back to queue
    │   └─→ else:
    │       └─→ UPDATE status='failed', error=str(e)

Download Function
├─→ parse_m3u8(url)
│   ├─→ requests.get(url, headers)
│   ├─→ m3u8.loads(content)
│   └─→ return segments[]
│
├─→ download_segments(segments)
│   ├─→ with ThreadPoolExecutor(10):
│   │   └─→ for seg in segments:
│   │       ├─→ download_file(seg.url)
│   │       └─→ update_progress()
│   └─→ return segment_files[]
│
└─→ merge_with_ffmpeg(segment_files)
    ├─→ subprocess.run(['ffmpeg', '-i', ...])
    └─→ return output_file
```

---

## 4. Database Schema (PostgreSQL)

```sql
┌─────────────────────────────────────────────────────────────┐
│                        jobs table                            │
├──────────────┬──────────────┬──────────────────────────────┤
│ Column       │ Type         │ Description                   │
├──────────────┼──────────────┼──────────────────────────────┤
│ id           │ UUID         │ Primary key                   │
│ url          │ TEXT         │ M3U8 URL                      │
│ title        │ VARCHAR(255) │ Video title                   │
│ status       │ VARCHAR(20)  │ pending/downloading/...       │
│ progress     │ INTEGER      │ 0-100                         │
│ created_at   │ TIMESTAMP    │ Job creation time             │
│ started_at   │ TIMESTAMP    │ Download start time           │
│ completed_at │ TIMESTAMP    │ Completion time               │
│ file_size    │ BIGINT       │ File size in bytes            │
│ file_path    │ TEXT         │ Path to completed file        │
│ error_msg    │ TEXT         │ Error message if failed       │
│ retry_count  │ INTEGER      │ Number of retry attempts      │
└──────────────┴──────────────┴──────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    job_metadata table                        │
├──────────────┬──────────────┬──────────────────────────────┤
│ Column       │ Type         │ Description                   │
├──────────────┼──────────────┼──────────────────────────────┤
│ job_id       │ UUID         │ FK to jobs(id)                │
│ referer      │ TEXT         │ HTTP Referer header           │
│ headers      │ JSONB        │ Additional headers            │
│ source_page  │ TEXT         │ Origin page URL               │
│ resolution   │ VARCHAR(20)  │ Video resolution              │
│ duration     │ INTEGER      │ Video duration (seconds)      │
│ segment_count│ INTEGER      │ Total segments                │
└──────────────┴──────────────┴──────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      config table                            │
├──────────────┬──────────────┬──────────────────────────────┤
│ Column       │ Type         │ Description                   │
├──────────────┼──────────────┼──────────────────────────────┤
│ key          │ VARCHAR(100) │ Primary key                   │
│ value        │ TEXT         │ Configuration value           │
│ updated_at   │ TIMESTAMP    │ Last update time              │
└──────────────┴──────────────┴──────────────────────────────┘

Indexes:
  - idx_jobs_status ON jobs(status)
  - idx_jobs_created ON jobs(created_at DESC)
  - idx_jobs_completed ON jobs(completed_at DESC)
```

---

## 5. Redis Data Structures

```
┌─────────────────────────────────────────────────────────────┐
│                     Redis Keys & Types                       │
└─────────────────────────────────────────────────────────────┘

1. Job Queue (List)
   Key: "download_queue"
   Type: LIST
   Operations:
     - RPUSH download_queue {job_id}  # Enqueue
     - BLPOP download_queue 0         # Dequeue (blocking)
     - LLEN download_queue            # Queue length

2. Active Jobs (Set)
   Key: "active_jobs"
   Type: SET
   Operations:
     - SADD active_jobs {job_id}      # Mark as active
     - SREM active_jobs {job_id}      # Remove when done
     - SCARD active_jobs              # Count active

3. Job Progress (Hash)
   Key: "progress:{job_id}"
   Type: HASH
   Fields:
     - downloaded_segments: 42
     - total_segments: 100
     - current_speed: "5.2 MB/s"
     - eta: "120 seconds"
   TTL: 86400 (24 hours)

4. Rate Limiting (String)
   Key: "ratelimit:{ip}"
   Type: STRING
   Value: request_count
   TTL: 60 (1 minute)
   Operations:
     - INCR ratelimit:{ip}
     - EXPIRE ratelimit:{ip} 60
     - GET ratelimit:{ip}
```

---

## 6. Security Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Security Layers                            │
└──────────────────────────────────────────────────────────────┘

Layer 1: Network Security
┌─────────────────────────────────────┐
│ Chrome Extension                     │
│ └─→ HTTPS only                      │
│     └─→ Certificate validation      │
└───────────┬─────────────────────────┘
            │ TLS 1.3
            ↓
┌─────────────────────────────────────┐
│ Firewall / Reverse Proxy            │
│ ├─→ IP whitelist (optional)         │
│ ├─→ Rate limiting                   │
│ └─→ DDoS protection                 │
└───────────┬─────────────────────────┘
            │
            ↓
┌─────────────────────────────────────┐
│ NAS Internal Network                │
│ └─→ Docker bridge network           │
└─────────────────────────────────────┘

Layer 2: Authentication
┌─────────────────────────────────────┐
│ Every API Request                   │
│ Header: Authorization: Bearer TOKEN │
└───────────┬─────────────────────────┘
            │
            ↓
┌─────────────────────────────────────┐
│ API Middleware                      │
│ ├─→ Validate API key                │
│ ├─→ Check rate limit                │
│ └─→ Log request                     │
└───────────┬─────────────────────────┘
            │
            ├─→ Valid → Continue
            └─→ Invalid → 401 Unauthorized

Layer 3: Input Validation
┌─────────────────────────────────────┐
│ URL Validation                      │
│ ├─→ Must start with https://        │
│ ├─→ Must end with .m3u8             │
│ └─→ Regex validation                │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ Filename Sanitization               │
│ ├─→ Remove path traversal (..)      │
│ ├─→ Remove special chars            │
│ └─→ Limit length                    │
└─────────────────────────────────────┘

Layer 4: Execution Isolation
┌─────────────────────────────────────┐
│ Docker Containers                   │
│ ├─→ Non-root user                   │
│ ├─→ Read-only filesystem            │
│ ├─→ Limited resources                │
│ └─→ No privileged mode              │
└─────────────────────────────────────┘
```

---

## 7. Error Handling Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   Error Handling Strategy                    │
└─────────────────────────────────────────────────────────────┘

Network Errors
├─→ Connection timeout
│   ├─→ Retry: 3 attempts
│   ├─→ Backoff: exponential (1s, 2s, 4s)
│   └─→ If all fail → status='failed'
│
├─→ 404 Not Found
│   └─→ No retry → status='failed'
│
├─→ 403 Forbidden
│   └─→ No retry → status='failed'
│       └─→ error_msg = "Access denied"
│
└─→ 500 Server Error
    └─→ Retry: 2 attempts
        └─→ If fail → status='failed'

Parsing Errors
├─→ Invalid m3u8 format
│   └─→ No retry → status='failed'
│       └─→ error_msg = "Invalid m3u8"
│
└─→ Empty playlist
    └─→ No retry → status='failed'
        └─→ error_msg = "No segments found"

Storage Errors
├─→ Disk full
│   ├─→ Pause queue
│   ├─→ Alert admin
│   └─→ Put job back in queue
│
└─→ Permission denied
    └─→ Fatal error → restart container

FFmpeg Errors
├─→ Codec error
│   ├─→ Try alternative command
│   └─→ If fail → status='failed'
│
└─→ Corrupted segment
    ├─→ Retry segment download
    └─→ If fail → skip segment (lossy)

All Errors
└─→ Log to:
    ├─→ Database (error_msg column)
    ├─→ File (/logs/app.log)
    └─→ Optional: Alert (email/telegram)
```

---

## 8. Performance Optimization

```
┌─────────────────────────────────────────────────────────────┐
│                  Performance Strategies                      │
└─────────────────────────────────────────────────────────────┘

1. Concurrent Processing
   ┌──────────────────────────────┐
   │ Worker Pool                  │
   │ ├─→ 10 threads per video     │
   │ ├─→ 3 videos concurrently    │
   │ └─→ Total: 30 active threads │
   └──────────────────────────────┘

2. Caching
   ┌──────────────────────────────┐
   │ Redis Cache                  │
   │ ├─→ Job status (TTL: 1 hour) │
   │ ├─→ System stats (TTL: 30s)  │
   │ └─→ Hit rate target: >80%    │
   └──────────────────────────────┘

3. Database Optimization
   ┌──────────────────────────────┐
   │ Indexes                      │
   │ ├─→ status (for filtering)   │
   │ ├─→ created_at (for sorting) │
   │ └─→ Query time: <50ms        │
   └──────────────────────────────┘

4. Network Optimization
   ┌──────────────────────────────┐
   │ Connection Pooling           │
   │ ├─→ Reuse HTTP connections   │
   │ ├─→ Keep-alive enabled       │
   │ └─→ Pool size: 20            │
   └──────────────────────────────┘

5. Storage Optimization
   ┌──────────────────────────────┐
   │ Direct Write                 │
   │ ├─→ No temp files (if poss.) │
   │ ├─→ Stream to disk           │
   │ └─→ Reduce I/O operations    │
   └──────────────────────────────┘

Expected Performance:
  - 1080p video (1GB): ~10-15 minutes
  - Throughput: 4-8 MB/s
  - Concurrent downloads: 3-5 (depending on NAS)
  - CPU usage: 50-70% during merge
  - RAM usage: ~500MB per video
```

---

## 9. Monitoring & Observability

```
┌─────────────────────────────────────────────────────────────┐
│                    Monitoring Stack                          │
└─────────────────────────────────────────────────────────────┘

Logs
├─→ Application Logs
│   ├─→ Format: JSON
│   ├─→ Level: INFO (production)
│   ├─→ Rotation: Daily
│   └─→ Retention: 30 days
│
├─→ Access Logs (nginx)
│   └─→ Format: Combined
│
└─→ Error Logs
    └─→ Level: ERROR, CRITICAL

Metrics to Track
├─→ Download Metrics
│   ├─→ Success rate
│   ├─→ Average duration
│   ├─→ Queue length
│   └─→ Active downloads
│
├─→ System Metrics
│   ├─→ CPU usage
│   ├─→ RAM usage
│   ├─→ Disk usage
│   └─→ Network throughput
│
└─→ API Metrics
    ├─→ Request count
    ├─→ Response time (p50, p95, p99)
    ├─→ Error rate
    └─→ Rate limit hits

Alerting Rules
├─→ Disk >90% → Alert
├─→ Error rate >5% → Alert
├─→ Queue >50 jobs → Warning
└─→ Worker down → Critical
```

---

## 10. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Production Deployment                     │
└─────────────────────────────────────────────────────────────┘

Internet
    │
    ↓
┌───────────────┐
│ Router/Firewall│
│ Port: 443      │
└───────┬────────┘
        │ NAT / Port Forward
        ↓
┌─────────────────────────────────────┐
│ NAS (192.168.1.100)                 │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Docker Host                     │ │
│ │                                 │ │
│ │ docker-compose.yml              │ │
│ │ ├─→ nginx (reverse proxy)      │ │
│ │ │   └─→ SSL cert (Let's Encrypt)│ │
│ │ ├─→ api (FastAPI)               │ │
│ │ ├─→ worker (Python)             │ │
│ │ ├─→ db (PostgreSQL)             │ │
│ │ └─→ redis                       │ │
│ │                                 │ │
│ │ Volumes:                        │ │
│ │ ├─→ /volume1/downloads          │ │
│ │ ├─→ /volume1/docker/db_data     │ │
│ │ └─→ /volume1/docker/logs        │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘

Alternative: Tailscale VPN
Internet
    │
    ↓
┌───────────────┐
│ Tailscale     │
│ Coordination  │
│ Server        │
└───┬───────┬───┘
    │       │
    ↓       ↓
Chrome    NAS
(User)  (Private IP)
          └─→ No port forwarding needed
          └─→ Encrypted tunnel
```

---

## Summary

This architecture provides:
- ✅ **Scalability**: Queue-based design supports multiple workers
- ✅ **Reliability**: Retry logic, error handling, persistence
- ✅ **Security**: Multi-layer authentication and validation
- ✅ **Observability**: Comprehensive logging and monitoring
- ✅ **Performance**: Concurrent downloads, caching, optimizations
- ✅ **Maintainability**: Clear separation of concerns, documented

For implementation details, see [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md).

