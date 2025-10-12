# Installation Guide

Complete installation guide for Chrome2NAS M3U8 Downloader.

## Quick Navigation

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Synology NAS Setup](#synology-nas-setup)
- [Standard Docker Setup](#standard-docker-setup)
- [Chrome Extension Setup](#chrome-extension-setup)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements
- **NAS/Server**: 2GB+ RAM, 2+ CPU cores, Docker support
- **Client**: Chrome browser (v88+)

### Software Requirements
- Docker 20.10+
- Docker Compose 2.0+
- Network connectivity between Chrome and NAS

---

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/chrome2nas-m3u8.git
cd chrome2nas-m3u8/docker
```

### 2. Configure Environment
```bash
# Generate secure credentials
API_KEY=$(openssl rand -base64 32)
DB_PASSWORD=$(openssl rand -base64 24)

# Create .env file
cat > .env << EOF
DB_PASSWORD=${DB_PASSWORD}
API_KEY=${API_KEY}
MAX_CONCURRENT_DOWNLOADS=3
MAX_DOWNLOAD_WORKERS=10
MAX_RETRY_ATTEMPTS=3
FFMPEG_THREADS=4
LOG_LEVEL=INFO
ALLOWED_ORIGINS=chrome-extension://*
RATE_LIMIT_PER_MINUTE=10
STORAGE_PATH=/volume1/downloads/m3u8
EOF

# Save your API key for Chrome extension
echo "Your API Key: ${API_KEY}"
```


### 3. Deploy Services
```bash
# For Synology NAS
sudo docker-compose -f docker-compose.synology.yml up -d

# For standard Docker
docker-compose up -d
```

### 4. Verify Deployment
```bash
# Check health
curl http://localhost:52052/api/health

# View logs
docker logs m3u8_api
docker logs m3u8_worker
```

### 6. Install Chrome Extension
1. Open `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select `chrome-extension` folder
5. Configure with your NAS IP and API key

---

## Synology NAS Setup

### Step 1: Install Docker
1. Open **Package Center**
2. Search and install **Docker** and **Container Manager**

### Step 2: Enable SSH (Optional but Recommended)
1. **Control Panel** → **Terminal & SNMP**
2. Enable **SSH service**

### Step 3: Create Directory Structure
```bash
# SSH into your Synology
ssh your-username@synology-ip

# Create directories
sudo mkdir -p /volume1/docker/m3u8-downloader
sudo mkdir -p /volume1/xxxxyyyy-m3u8/downloads/{completed,processing,failed}
```

> **⚠️ Important: Download Folder Configuration**
>
> - **Custom Location**: The download folder path can be customized in `docker-compose.yml` (or `docker-compose.synology.yml`). Edit the volume mappings for both `api` and `worker` services:
>   ```yaml
>   volumes:
>     - /your/custom/path:/downloads  # Change this path
>   ```
> - **Required Structure**: The download folder **must** contain three subdirectories:
>   - `completed/` - Successfully downloaded files
>   - `processing/` - Files currently being processed
>   - `failed/` - Failed downloads for review
> - If you change the download location, ensure these subdirectories exist before starting the services.

### Step 4: Upload Project Files

**Option A: Using File Station**
1. Download project ZIP from GitHub
2. Extract locally
3. Upload `docker` folder to `/volume1/docker/m3u8-downloader/`

**Option B: Using Git (if available)**
```bash
cd /volume1/docker
git clone https://github.com/yourusername/chrome2nas-m3u8.git m3u8-downloader
```

### Step 5: Configure Environment
```bash
cd /volume1/docker/m3u8-downloader/docker

# Create .env file
cat > .env << 'EOF'
DB_PASSWORD=your_secure_password_here
API_KEY=your_api_key_minimum_32_chars
MAX_CONCURRENT_DOWNLOADS=3
MAX_DOWNLOAD_WORKERS=10
MAX_RETRY_ATTEMPTS=3
FFMPEG_THREADS=4
LOG_LEVEL=INFO
ALLOWED_ORIGINS=chrome-extension://*
RATE_LIMIT_PER_MINUTE=10
EOF

# Generate secure keys
openssl rand -base64 32  # Use this for API_KEY
openssl rand -base64 24  # Use this for DB_PASSWORD

# Edit .env with generated keys
sudo nano .env
```

### Step 6: Deploy on Synology
```bash
cd /volume1/docker/m3u8-downloader/docker

# Start services
sudo docker-compose -f docker-compose.synology.yml up -d

# Check status
sudo docker ps

# View logs
sudo docker logs m3u8_api
sudo docker logs m3u8_worker
```

### Step 7: Configure Firewall
1. **Control Panel** → **Security** → **Firewall**
2. Create rule to allow port 52052
3. Source: Your local network

### Step 8: Test API
```bash
curl http://YOUR_SYNOLOGY_IP:52052/api/health
# Should return: {"status":"healthy"}
```

---

## Standard Docker Setup

### For Ubuntu/Debian

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Clone project
git clone https://github.com/yourusername/chrome2nas-m3u8.git
cd chrome2nas-m3u8/docker

# Configure environment (see Quick Start section)
# Create .env file with your settings

# Create download folder structure
mkdir -p ../downloads/{completed,processing,failed}

# Deploy
docker-compose up -d

# Check status
docker ps
curl http://localhost:52052/api/health
```

### For Other Linux Distributions
Similar steps - install Docker, Docker Compose, then follow Quick Start.

---

## Chrome Extension Setup

### Step 1: Prepare Icons

**Option A: Use Existing Icons**
Icons should already be in `chrome-extension/icons/` (icon16.png, icon48.png, icon128.png)

**Option B: Create Your Own**
Create three PNG files:
- `icon16.png` (16×16px)
- `icon48.png` (48×48px)
- `icon128.png` (128×128px)

Place them in `chrome-extension/icons/`

### Step 2: Load Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right corner)
3. Click **Load unpacked**
4. Select the `chrome-extension` folder
5. Extension should appear in your toolbar

### Step 3: Configure Extension

1. Click the extension icon in Chrome toolbar
2. Click the **⚙️ Settings** button
3. Enter your settings:
   - **NAS Endpoint**: `http://YOUR_NAS_IP:52052`
   - **API Key**: Paste from your `.env` file
4. Click **Test Connection**
   - Should show: "✅ Connected! Active downloads: 0, Queue: 0"
5. Click **Save Settings**

### Step 4: Enable Auto-Detection (Optional)
- Check **Auto-detect M3U8 URLs** in settings
- Extension will automatically detect video streams

---

## Testing

### Test 1: API Health Check
```bash
curl http://YOUR_NAS_IP:52052/api/health
# Expected: {"status":"healthy"}
```

### Test 2: Submit Test Download
```bash
export API_KEY="your_api_key_here"

curl -X POST http://YOUR_NAS_IP:52052/api/download \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
    "title": "Test Video"
  }'
```

### Test 3: Check Download Status
```bash
curl http://YOUR_NAS_IP:52052/api/jobs \
  -H "Authorization: Bearer $API_KEY"
```

### Test 4: Monitor Worker
```bash
# View real-time logs
docker logs -f m3u8_worker

# Check for completed downloads
ls -lh /volume1/downloads/m3u8/completed/
```

### Test 5: Use Chrome Extension
1. Visit a video streaming site
2. Extension badge should show detected URLs
3. Click extension icon
4. Click "Send to NAS"
5. Monitor progress in extension popup

---

## Troubleshooting

### Issue: Containers Won't Start

```bash
# Check logs
docker-compose logs

# Common solutions:
# 1. Port conflicts
sudo netstat -tulpn | grep -E '52052|5432|6379'

# 2. Permission issues (Synology)
sudo docker-compose -f docker-compose.synology.yml up -d

# 3. Missing .env file
ls -la .env
```

### Issue: Extension Can't Connect

**Check 1: Network Connectivity**
```bash
# From your computer
ping YOUR_NAS_IP
curl http://YOUR_NAS_IP:52052/api/health
```

**Check 2: Firewall**
- Ensure NAS firewall allows the port
- Check router/network firewall

**Check 3: Correct Endpoint**
- Verify IP address
- Verify port (52052)
- Don't forget `http://` prefix

### Issue: Downloads Fail

```bash
# Check worker logs
docker logs m3u8_worker

# Common causes:
# 1. Invalid M3U8 URL
# 2. Network connectivity issues
# 3. Disk space full
df -h

# 4. Permission issues
ls -ld /volume1/downloads/m3u8/
```

### Issue: Slow Performance

**Check System Resources**
```bash
# CPU and memory usage
docker stats

# Adjust settings in .env
MAX_CONCURRENT_DOWNLOADS=2  # Reduce if overloaded
MAX_DOWNLOAD_WORKERS=5      # Reduce per-video threads
FFMPEG_THREADS=2            # Reduce FFmpeg threads
```

**Restart Services**
```bash
docker-compose restart worker
```

### Issue: Video Won't Play

```bash
# Check video file
file /path/to/video.mp4

# Check FFmpeg logs
docker logs m3u8_worker | grep -i ffmpeg

# Try re-downloading with lower settings
```

---

## Performance Tuning

### High-End System (8GB+ RAM, 4+ cores)
```env
MAX_CONCURRENT_DOWNLOADS=5
MAX_DOWNLOAD_WORKERS=15
FFMPEG_THREADS=6
```

### Mid-Range System (4GB RAM, 2-4 cores)
```env
MAX_CONCURRENT_DOWNLOADS=3
MAX_DOWNLOAD_WORKERS=10
FFMPEG_THREADS=4
```

### Entry-Level System (2GB RAM)
```env
MAX_CONCURRENT_DOWNLOADS=2
MAX_DOWNLOAD_WORKERS=5
FFMPEG_THREADS=2
```

---

## Security Best Practices

1. **Use Strong Credentials**
   ```bash
   # Generate secure keys
   openssl rand -base64 32
   ```

2. **Enable HTTPS** (Production)
   - Use Synology's reverse proxy with SSL
   - Or configure nginx with Let's Encrypt

3. **Restrict Access**
   - Use firewall rules
   - Consider VPN/Tailscale for remote access

4. **Regular Updates**
   ```bash
   git pull
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

---

## Next Steps

- Read [Architecture Documentation](docs/ARCHITECTURE.md)
- Check [API Specification](docs/SPECIFICATION.md)
- Review [Security Policy](SECURITY.md)
- See [Contributing Guidelines](CONTRIBUTING.md)

---

## Support

- **Documentation**: Check the [docs](docs/) folder
- **Issues**: [GitHub Issues](https://github.com/yourusername/chrome2nas-m3u8/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/chrome2nas-m3u8/discussions)

---

**Installation Complete!** 🎉 Enjoy your automated M3U8 downloader!

