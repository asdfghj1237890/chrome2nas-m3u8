# Chrome2NAS M3U8 Downloader

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docs.docker.com/compose/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Chrome Extension](https://img.shields.io/badge/Chrome-Extension-red.svg)](https://developer.chrome.com/docs/extensions/)
[![Release](https://img.shields.io/github/v/release/asdfghj1237890/chrome2nas-m3u8)](https://github.com/asdfghj1237890/chrome2nas-m3u8/releases/latest)

> Seamlessly capture M3U8 and MP4 video streams from Chrome and download them to your NAS

## Overview

This system enables you to:
1. 🔍 Detect M3U8 and MP4 video URLs in Chrome
2. 📤 Send URLs to your NAS with one click
3. ⬇️ Automatically download and convert to MP4
4. 💾 Store videos on your NAS storage

## System Architecture

```
Chrome Extension → NAS Docker (API + Worker) → Video Storage
```

![Overall System Architecture](pics/overall_system_architecture.png)

### Backend Architecture

![Backend Architecture](pics/backend_architecture.png)

## Quick Links

<img align="right" src="docs/extension-screenshot.png" alt="Chrome Extension Screenshot" width="300">
<p align="right"><sub>Chrome Extension Interface (Click to view full size)</sub></p>

- **[🚀 Installation Guide](INSTALL.md)** - Complete setup instructions
- **[📋 Technical Documentation](docs/)** - Architecture & specifications
- **[🔒 Security Policy](SECURITY.md)** - Security guidelines
- **[🤝 Contributing](CONTRIBUTING.md)** - How to contribute



## Key Features

### Chrome Extension
- ✅ Automatic M3U8 and MP4 URL detection
- ✅ One-click send to NAS
- ✅ Side panel interface for easy access
- ✅ Real-time download progress
- ✅ Cookie & header forwarding for authenticated streams
- ✅ Context menu integration
- ✅ Configurable NAS endpoint

### NAS Docker Service
- ✅ RESTful API for job management
- ✅ **Dual-worker architecture** for parallel processing
- ✅ Multi-threaded segment downloader
- ✅ FFmpeg-based video merging
- ✅ Job queue with Redis
- ✅ Progress tracking & notifications
- ✅ Persistent storage with PostgreSQL

## Technology Stack

**Frontend:**
- Chrome Extension (Manifest V3)
- JavaScript ES6+

**Backend:**
- Python 3.11+ (FastAPI)
- FFmpeg
- Redis
- PostgreSQL
- Docker & Docker Compose

<br clear="both">

## Project Status

🎉 **All Core Phases Complete!**

### Implementation Phases
- [x] Phase 0: Technical specification ✅
- [x] Phase 1: Core infrastructure (Docker, API, Database) ✅
  - Docker Compose configuration
  - Synology-optimized setup
  - PostgreSQL database with schema
  - Redis job queue
  - FastAPI basic endpoints
  - Download worker skeleton
- [x] Phase 2: Download worker (M3U8 parser, FFmpeg integration) ✅
  - Dual-worker architecture (2 workers by default)
  - M3U8 playlist parser
  - Multi-threaded segment downloader
  - FFmpeg video merger
  - Progress tracking
  - Retry mechanism
- [x] Phase 3: Chrome extension (URL detection, UI) ✅
  - Automatic M3U8 and MP4 detection
  - One-click send to NAS
  - Side panel interface
  - Real-time progress monitoring
  - Cookie & header forwarding
  - Settings management
  - Context menu integration
  - Badge notifications
- [ ] Phase 4: Integration testing & optimization
- [ ] Phase 5: Production hardening & best practices

## Project Structure

```
chrome2nas-m3u8/
├── chrome-extension/  # Chrome extension source
├── docker/            # Docker services (API + Worker)
├── docs/              # Documentation
├── tests/             # Test suites
├── SPECIFICATION.md   # Technical specification
└── README.md          # This file
```

## Requirements

### For NAS
- Docker & Docker Compose
- 2GB+ RAM available
- Storage space for videos
- Network accessibility from Chrome device

### For Chrome
- Chrome browser (v88+)
- Developer mode enabled (for unpacked extension)

## Getting Started

### 📦 Installation

**[→ Complete Installation Guide](INSTALL.md)** - Step-by-step setup for all platforms

**Quick setup for Synology NAS:**
```bash
# 1. Download latest release assets
curl -L -o chrome2nas-docker.zip https://github.com/asdfghj1237890/chrome2nas-m3u8/releases/latest/download/chrome2nas-m3u8-downloader-docker.zip

# 2. Unzip Docker package
unzip chrome2nas-docker.zip -d m3u8-downloader
cd m3u8-downloader/docker
#    remove the docker-compose.yml and rename the docker-compose.synology.yml to docker-compose.yml

# 3. Create .env file with your OWN credentials
cat > .env << EOF
DB_PASSWORD=$(YOUR OWN PASSWORD)
API_KEY=$(YOUR OWN API KEY)
MAX_CONCURRENT_DOWNLOADS=3
MAX_DOWNLOAD_WORKERS=10
LOG_LEVEL=INFO
ALLOWED_ORIGINS=chrome-extension://*
EOF

# 4. Deploy services
#    go to projects in the container manager, create one and select the path "m3u8-downloader/docker"
#    the system can find the docker-compose.yml to install the whole project

# 5. Install Chrome extension: unzip chrome2nas-extension.zip and load the
#    unzipped folder in Chrome (Developer mode → Load unpacked)
```

For detailed instructions including Synology NAS setup, see **[INSTALL.md](INSTALL.md)**

### Current Status: Core Features Complete ✅

You can now:
- ✅ Deploy Docker stack on Synology NAS or any Docker host
- ✅ Download M3U8 video streams to MP4
- ✅ Download MP4 videos directly
- ✅ Use Chrome extension for automatic detection (M3U8 & MP4)
- ✅ Forward cookies & headers for authenticated streams
- ✅ Monitor download progress in side panel
- ✅ Manage downloads via REST API

## Usage

1. Browse to any video streaming site
2. When video URL (M3U8/MP4) is detected, extension badge shows notification
3. Click extension icon to open side panel, or right-click → "Send to NAS"
4. Video downloads automatically to your NAS (with cookies for authenticated streams)
5. Monitor progress in the side panel
6. Access completed videos in `/downloads/completed/`

## Configuration

### Environment Variables (.env)
```bash
API_KEY=your-secure-api-key
NAS_STORAGE_PATH=/volume1/downloads/m3u8
DATABASE_URL=postgresql://postgres:password@db:5432/m3u8_db
REDIS_URL=redis://redis:6379
MAX_CONCURRENT_DOWNLOADS=3  # Per worker (2 workers = 6 total)
MAX_DOWNLOAD_WORKERS=10      # Threads per video
FFMPEG_THREADS=4
```

### Worker Scaling
The system runs **2 workers** by default for parallel processing:
- **Total capacity**: Up to 6 videos simultaneously (3 per worker)
- **Scale up**: Add more workers in `docker-compose.yml` for higher throughput
- **Scale down**: Remove `worker2` service for lower-spec NAS devices

### Extension Settings
- **NAS Endpoint**: `https://192.168.1.100:52052`
- **API Key**: Your configured API key
- **Auto Detect**: Enable automatic M3U8/MP4 detection
- **Notifications**: Enable completion notifications

> **Note**: Click the extension icon to open the side panel for managing detected videos and monitoring downloads.

## Security Notes

⚠️ **Important Security Considerations:**
- Use HTTPS with valid SSL certificate
- Keep API key secret
- Consider using VPN/Tailscale for remote access
- Implement rate limiting
- Regularly update Docker images

## Limitations

- ❌ DRM-protected content not supported
- ❌ Some streaming sites use additional encryption
- ❌ Requires network connectivity between Chrome and NAS
- ℹ️ Download speed limited by network and NAS hardware

## Troubleshooting

### Extension can't connect to NAS
- Verify NAS IP and port
- Check firewall rules
- Ensure Docker service is running: `docker-compose ps`

### Download fails
- Check logs: `docker-compose logs worker`
- Verify video URL is accessible
- Check disk space on NAS
- For authenticated streams, ensure cookies are being captured

### Slow downloads
- Reduce concurrent downloads in .env
- Check NAS CPU/RAM usage
- Verify network bandwidth

## Contributing

Contributions welcome! Please:
1. Review the specification first
2. Follow existing code style
3. Add tests for new features
4. Update documentation

## License

MIT License - See LICENSE file for details

## Documentation

- 📖 [Installation Guide](INSTALL.md) - Complete setup instructions
- 🏗️ [Technical Documentation](docs/) - Architecture, specifications, and implementation details
- 🔒 [Security Policy](SECURITY.md) - Security guidelines and reporting
- 🤝 [Contributing](CONTRIBUTING.md) - How to contribute
- 📝 [Changelog](CHANGELOG.md) - Version history

## Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/asdfghj1237890/chrome2nas-m3u8/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/asdfghj1237890/chrome2nas-m3u8/discussions)
- 📧 **Security**: See [SECURITY.md](SECURITY.md) for reporting vulnerabilities

---

**Status**: Core Features Complete | Production Ready  
**Version**: 1.4.0  
**Last Updated**: 2025-12-04  
**Port**: 52052 (unified)

## Star History

If you find this project useful, please consider giving it a star! ⭐

