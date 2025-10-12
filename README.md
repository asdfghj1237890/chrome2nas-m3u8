# Chrome2NAS M3U8 Downloader

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docs.docker.com/compose/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Chrome Extension](https://img.shields.io/badge/Chrome-Extension-red.svg)](https://developer.chrome.com/docs/extensions/)

> Seamlessly capture m3u8 video streams from Chrome and download them to your NAS

## Overview

This system enables you to:
1. 🔍 Detect m3u8 video stream URLs in Chrome
2. 📤 Send URLs to your NAS with one click
3. ⬇️ Automatically download and convert to MP4
4. 💾 Store videos on your NAS storage

## System Architecture

```
Chrome Extension → NAS Docker (API + Worker) → Video Storage
```

## Quick Links

- **[🚀 Installation Guide](INSTALL.md)** - Complete setup instructions
- **[📋 Technical Documentation](docs/)** - Architecture & specifications
- **[🔒 Security Policy](SECURITY.md)** - Security guidelines
- **[🤝 Contributing](CONTRIBUTING.md)** - How to contribute

## Key Features

### Chrome Extension
- ✅ Automatic m3u8 URL detection
- ✅ One-click send to NAS
- ✅ Real-time download progress
- ✅ Context menu integration
- ✅ Configurable NAS endpoint

### NAS Docker Service
- ✅ RESTful API for job management
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
  - M3U8 playlist parser
  - Multi-threaded segment downloader
  - FFmpeg video merger
  - Progress tracking
  - Retry mechanism
- [x] Phase 3: Chrome extension (URL detection, UI) ✅
  - Automatic M3U8 detection
  - One-click send to NAS
  - Real-time progress monitoring
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

**Quick setup:**
```bash
# 1. Clone repository
git clone https://github.com/asdfghj1237890/chrome2nas-m3u8.git
cd chrome2nas-m3u8/docker

# 2. Create .env file with your credentials
cat > .env << EOF
DB_PASSWORD=$(openssl rand -base64 24)
API_KEY=$(openssl rand -base64 32)
MAX_CONCURRENT_DOWNLOADS=3
MAX_DOWNLOAD_WORKERS=10
LOG_LEVEL=INFO
ALLOWED_ORIGINS=chrome-extension://*
EOF

# 3. Deploy services
docker-compose up -d

# 4. Install Chrome extension from chrome-extension/ folder
```

For detailed instructions including Synology NAS setup, see **[INSTALL.md](INSTALL.md)**

### Current Status: Core Features Complete ✅

You can now:
- ✅ Deploy Docker stack on Synology NAS or any Docker host
- ✅ Download M3U8 video streams to MP4
- ✅ Use Chrome extension for automatic detection
- ✅ Monitor download progress in real-time
- ✅ Manage downloads via REST API

## Usage

1. Browse to any video streaming site
2. When m3u8 URL is detected, extension badge shows notification
3. Click extension icon or right-click → "Send to NAS"
4. Video downloads automatically to your NAS
5. Monitor progress in extension popup
6. Access completed videos in `/downloads/completed/`

## Configuration

### Environment Variables (.env)
```bash
API_KEY=your-secure-api-key
NAS_STORAGE_PATH=/volume1/downloads/m3u8
DATABASE_URL=postgresql://postgres:password@db:5432/m3u8_db
REDIS_URL=redis://redis:6379
MAX_CONCURRENT_DOWNLOADS=3
FFMPEG_THREADS=4
```

### Extension Settings
- **NAS Endpoint**: `https://192.168.1.100:52052`
- **API Key**: Your configured API key
- **Auto Detect**: Enable automatic m3u8 detection
- **Notifications**: Enable completion notifications

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
- Verify m3u8 URL is accessible
- Check disk space on NAS

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
**Version**: 1.0.3
**Last Updated**: 2025-10-12  
**Port**: 52052 (unified)

## Star History

If you find this project useful, please consider giving it a star! ⭐

