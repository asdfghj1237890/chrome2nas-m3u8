# Implementation Roadmap

This document provides a step-by-step guide for implementing the Chrome2NAS M3U8 Downloader system.

## Prerequisites

Before starting implementation:
- [x] Technical specification completed
- [ ] Development environment setup
- [ ] NAS access configured
- [ ] Domain knowledge of:
  - Chrome Extensions API
  - Docker & Docker Compose
  - M3U8 protocol
  - FFmpeg usage
  - REST API design

---

## Phase 1: Core Infrastructure (Est: 3-5 days)

### 1.1 Project Setup
**Files to create:**
```
docker/
├── docker-compose.yml
├── .dockerignore
└── init-db.sql
```

**Tasks:**
- [ ] Create Docker Compose configuration
- [ ] Setup PostgreSQL with initial schema
- [ ] Setup Redis for job queue
- [ ] Configure volume mounts for storage
- [ ] Test: `docker-compose up` starts all services

**Acceptance Criteria:**
- All containers start successfully
- Database accessible
- Redis accepting connections
- Volumes mounted correctly

### 1.2 Database Schema
**File:** `docker/init-db.sql`

**Tables to create:**
```sql
-- jobs table
CREATE TABLE jobs (
  id UUID PRIMARY KEY,
  url TEXT NOT NULL,
  title VARCHAR(255),
  status VARCHAR(20), -- pending, downloading, processing, completed, failed
  progress INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  file_size BIGINT,
  file_path TEXT,
  error_message TEXT
);

-- metadata table
CREATE TABLE job_metadata (
  job_id UUID REFERENCES jobs(id),
  referer TEXT,
  headers JSONB,
  source_page TEXT,
  resolution VARCHAR(20),
  duration INTEGER,
  PRIMARY KEY (job_id)
);

-- config table (for API keys, settings)
CREATE TABLE config (
  key VARCHAR(100) PRIMARY KEY,
  value TEXT,
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created ON jobs(created_at DESC);
```

**Tasks:**
- [ ] Design complete schema
- [ ] Add indexes for performance
- [ ] Create migration script
- [ ] Test: Manual insert and query

---

## Phase 2: API Gateway (Est: 4-6 days)

### 2.1 FastAPI Setup
**Directory:** `docker/api/`

**Files to create:**
```
api/
├── Dockerfile
├── requirements.txt
├── main.py
├── config.py
├── database.py
├── models.py
├── routers/
│   ├── __init__.py
│   ├── download.py
│   ├── jobs.py
│   └── auth.py
├── middleware/
│   ├── __init__.py
│   └── auth_middleware.py
└── utils/
    ├── __init__.py
    └── validators.py
```

**requirements.txt:**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
redis==5.0.1
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
```

### 2.2 Core Endpoints Implementation

**Tasks:**
- [ ] POST `/api/download` - Submit download job
  - Validate URL format
  - Generate job ID
  - Store in database
  - Push to Redis queue
  - Return job ID
  
- [ ] GET `/api/jobs` - List all jobs
  - Support pagination
  - Support filtering by status
  - Return job summary
  
- [ ] GET `/api/jobs/{id}` - Get job details
  - Return full job info
  - Include progress
  - Include metadata
  
- [ ] DELETE `/api/jobs/{id}` - Cancel job
  - Remove from queue if pending
  - Stop download if active
  - Update status
  
- [ ] GET `/api/status` - System status
  - Active downloads count
  - Queue length
  - Disk usage
  - System health

### 2.3 Authentication Middleware
- [ ] API key validation
- [ ] Rate limiting
- [ ] CORS configuration
- [ ] Request logging

**Test checklist:**
- [ ] All endpoints return correct status codes
- [ ] Invalid API key returns 401
- [ ] Invalid job ID returns 404
- [ ] Rate limiting works (11th request in 1 minute fails)
- [ ] CORS allows Chrome extension origin

---

## Phase 3: Download Worker (Est: 5-7 days)

### 3.1 Worker Setup
**Directory:** `docker/worker/`

**Files to create:**
```
worker/
├── Dockerfile
├── requirements.txt
├── worker.py
├── downloader.py
├── m3u8_parser.py
├── ffmpeg_wrapper.py
└── utils/
    ├── __init__.py
    ├── retry.py
    └── progress.py
```

**requirements.txt:**
```
redis==5.0.1
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
requests==2.31.0
m3u8==3.5.0
aiohttp==3.9.1
aiofiles==23.2.1
```

### 3.2 M3U8 Parser
**File:** `worker/m3u8_parser.py`

**Tasks:**
- [ ] Parse master playlist
- [ ] Extract variant streams (different qualities)
- [ ] Parse media playlist
- [ ] Extract all segment URLs
- [ ] Handle relative URLs
- [ ] Support AES-128 encryption info
- [ ] Detect total segments count

**Test cases:**
- [ ] Parse simple m3u8
- [ ] Parse m3u8 with variants
- [ ] Parse m3u8 with relative URLs
- [ ] Handle encrypted segments
- [ ] Handle live streams (fail gracefully)

### 3.3 Segment Downloader
**File:** `worker/downloader.py`

**Tasks:**
- [ ] Multi-threaded segment download (10 concurrent)
- [ ] Progress tracking (per segment)
- [ ] Retry logic (3 attempts with exponential backoff)
- [ ] Header forwarding (referer, user-agent, cookies)
- [ ] Download speed monitoring
- [ ] Disk space check before download
- [ ] Temporary file management

**Implementation:**
```python
class SegmentDownloader:
    def __init__(self, segments, headers, output_dir):
        self.segments = segments
        self.headers = headers
        self.output_dir = output_dir
        self.progress = 0
        
    async def download_segment(self, segment):
        # Download single segment with retry
        pass
        
    async def download_all(self):
        # Download all segments concurrently
        pass
        
    def get_progress(self):
        # Return progress percentage
        return (self.completed / self.total) * 100
```

### 3.4 FFmpeg Wrapper
**File:** `worker/ffmpeg_wrapper.py`

**Tasks:**
- [ ] Merge segments to MP4
- [ ] Handle different codecs
- [ ] Progress monitoring
- [ ] Error detection
- [ ] Cleanup temporary files

**FFmpeg command:**
```bash
ffmpeg -allowed_extensions ALL -i playlist.m3u8 -c copy -bsf:a aac_adtstoasc output.mp4
```

### 3.5 Worker Main Loop
**File:** `worker/worker.py`

**Tasks:**
- [ ] Connect to Redis queue
- [ ] Poll for new jobs
- [ ] Process job:
  1. Update status to "downloading"
  2. Parse m3u8
  3. Download segments
  4. Merge with FFmpeg
  5. Move to completed folder
  6. Update database
  7. Send notification (optional)
- [ ] Handle errors gracefully
- [ ] Support graceful shutdown

**Test checklist:**
- [ ] Worker processes job from queue
- [ ] Progress updates correctly in database
- [ ] Failed downloads marked as failed
- [ ] Completed files in correct directory
- [ ] Worker recovers from crashes
- [ ] Multiple workers can run concurrently

---

## Phase 4: Chrome Extension (Est: 5-7 days)

### 4.1 Extension Setup
**Directory:** `chrome-extension/`

**Files to create:**
```
chrome-extension/
├── manifest.json
├── background.js
├── popup/
│   ├── popup.html
│   ├── popup.css
│   └── popup.js
├── settings/
│   ├── settings.html
│   ├── settings.css
│   └── settings.js
├── icons/
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── utils/
    ├── api.js
    └── storage.js
```

### 4.2 Manifest Configuration
**File:** `chrome-extension/manifest.json`

```json
{
  "manifest_version": 3,
  "name": "Chrome2NAS M3U8 Downloader",
  "version": "1.0.0",
  "description": "Send m3u8 video streams to your NAS for download",
  "permissions": [
    "webRequest",
    "storage",
    "contextMenus",
    "notifications"
  ],
  "host_permissions": [
    "<all_urls>"
  ],
  "background": {
    "service_worker": "background.js"
  },
  "action": {
    "default_popup": "popup/popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },
  "options_page": "settings/settings.html"
}
```

### 4.3 Background Script (URL Detection)
**File:** `chrome-extension/background.js`

**Tasks:**
- [ ] Listen to `chrome.webRequest.onBeforeRequest`
- [ ] Filter for `.m3u8` URLs
- [ ] Store detected URLs in memory
- [ ] Update badge count when m3u8 detected
- [ ] Create context menu "Send to NAS"
- [ ] Handle context menu click
- [ ] Send to NAS API

**Implementation:**
```javascript
// Detect m3u8 URLs
chrome.webRequest.onBeforeRequest.addListener(
  function(details) {
    if (details.url.includes('.m3u8')) {
      detectedUrls.add(details.url);
      updateBadge();
    }
  },
  { urls: ["<all_urls>"] }
);

// Context menu
chrome.contextMenus.create({
  id: "sendToNAS",
  title: "Send to NAS",
  contexts: ["link", "page"]
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  sendToNAS(info.linkUrl || info.pageUrl);
});
```

### 4.4 Popup UI
**File:** `chrome-extension/popup/popup.html`

**Features:**
- [ ] List detected m3u8 URLs
- [ ] Send button for each URL
- [ ] Active downloads list with progress
- [ ] Settings button
- [ ] Connection status indicator

### 4.5 Settings Page
**File:** `chrome-extension/settings/settings.html`

**Features:**
- [ ] NAS endpoint input (IP + port)
- [ ] API key input
- [ ] Auto-detect toggle
- [ ] Notification preferences
- [ ] Test connection button
- [ ] Save button

### 4.6 API Communication
**File:** `chrome-extension/utils/api.js`

**Tasks:**
- [ ] POST to `/api/download`
- [ ] GET from `/api/jobs`
- [ ] Handle errors (network, 401, 500)
- [ ] Retry logic
- [ ] CORS handling

**Test checklist:**
- [ ] Extension detects m3u8 on test page
- [ ] Badge updates correctly
- [ ] Context menu appears
- [ ] Popup shows detected URLs
- [ ] Send to NAS works
- [ ] Progress updates in popup
- [ ] Settings save/load correctly
- [ ] Connection test works

---

## Phase 5: Integration & Testing (Est: 3-4 days)

### 5.1 End-to-End Testing
**Test scenarios:**
1. [ ] Fresh install flow
   - Install extension
   - Deploy Docker
   - Configure connection
   - Download first video

2. [ ] Happy path
   - Browse to streaming site
   - Detect m3u8
   - Send to NAS
   - Monitor progress
   - Verify completed file

3. [ ] Error scenarios
   - Invalid m3u8 URL
   - Network timeout
   - NAS offline
   - Disk full
   - Invalid API key

4. [ ] Concurrent downloads
   - Queue 5 videos
   - Verify all complete
   - Check performance

5. [ ] Resume after restart
   - Start download
   - Restart worker
   - Verify resume

### 5.2 Performance Testing
- [ ] Download 1GB video (benchmark time)
- [ ] 10 concurrent downloads
- [ ] Monitor CPU/RAM usage
- [ ] Monitor disk I/O

### 5.3 Security Testing
- [ ] API key validation
- [ ] SQL injection prevention
- [ ] Path traversal prevention
- [ ] Rate limiting enforcement
- [ ] HTTPS enforcement

---

## Phase 6: Documentation (Est: 2-3 days)

### 6.1 User Documentation
**Files to create:**
- [ ] `docs/INSTALLATION.md` - Step-by-step setup guide
- [ ] `docs/USER_GUIDE.md` - How to use the system
- [ ] `docs/TROUBLESHOOTING.md` - Common issues and solutions
- [ ] `docs/FAQ.md` - Frequently asked questions

### 6.2 Developer Documentation
- [ ] `docs/API.md` - Complete API reference
- [ ] `docs/ARCHITECTURE.md` - System architecture details
- [ ] `docs/CONTRIBUTING.md` - How to contribute
- [ ] `docs/DEVELOPMENT.md` - Local development setup

### 6.3 Video/Screenshot Documentation
- [ ] Installation walkthrough video
- [ ] Usage demonstration
- [ ] Screenshots for README

---

## Phase 7: Deployment & Polish (Est: 2-3 days)

### 7.1 Production Readiness
- [ ] Security hardening
  - Change default passwords
  - Generate secure API key
  - Setup HTTPS with Let's Encrypt
  - Configure firewall rules

- [ ] Monitoring setup
  - Log aggregation
  - Error alerting
  - Disk space monitoring

- [ ] Backup strategy
  - Database backups
  - Configuration backups

### 7.2 Chrome Web Store Preparation
- [ ] Create promotional images (1400x560, 440x280)
- [ ] Write store description
- [ ] Record demo video
- [ ] Prepare privacy policy
- [ ] Submit for review

### 7.3 Release Checklist
- [ ] Tag version v1.0.0
- [ ] Create GitHub release
- [ ] Publish Docker images to Docker Hub
- [ ] Update README with installation links
- [ ] Announce release

---

## Success Metrics

Track these metrics to measure success:
- Download success rate: Target > 95%
- Average download time: Target < 2x video duration
- User setup time: Target < 15 minutes
- System uptime: Target > 99%
- Bug reports: Target < 5 critical bugs in first month

---

## Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Infrastructure | 3-5 days | None |
| Phase 2: API Gateway | 4-6 days | Phase 1 |
| Phase 3: Worker | 5-7 days | Phase 1 |
| Phase 4: Extension | 5-7 days | Phase 2 |
| Phase 5: Testing | 3-4 days | All previous |
| Phase 6: Documentation | 2-3 days | All previous |
| Phase 7: Deployment | 2-3 days | All previous |

**Total estimated time: 24-35 days** (single developer, full-time)

---

## Next Steps

1. Review and approve this roadmap
2. Setup development environment
3. Create Git repository
4. Begin Phase 1: Core Infrastructure
5. Follow roadmap sequentially

---

**Status**: Planning Complete  
**Ready to Start**: Phase 1  
**Last Updated**: 2025-10-12

