#!/bin/bash
# Quick start script for Synology NAS
# Run this script to deploy the entire stack

set -e

echo "========================================="
echo "Chrome2NAS M3U8 Downloader"
echo "Synology Deployment Script"
echo "========================================="
echo ""

# Check if we're in the correct directory
if [ ! -f "docker-compose.synology.yml" ]; then
    echo "Error: docker-compose.synology.yml not found!"
    echo "Please run this script from the docker directory"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found!"
    echo "Creating .env from template..."
    
    cat > .env << 'EOF'
# Database
DB_PASSWORD=$(openssl rand -base64 32)

# API Key (please change this!)
API_KEY=$(openssl rand -base64 32)

# Worker Settings
MAX_CONCURRENT_DOWNLOADS=3
MAX_DOWNLOAD_WORKERS=10
MAX_RETRY_ATTEMPTS=3
FFMPEG_THREADS=4

# Logging
LOG_LEVEL=INFO

# Security
ALLOWED_ORIGINS=chrome-extension://*
RATE_LIMIT_PER_MINUTE=10
EOF
    
    echo "✓ .env file created"
    echo "⚠ Please edit .env and set your API_KEY!"
    echo ""
fi

# Check directories
echo "Checking directories..."

DIRS=(
    "/volume1/docker/m3u8-downloader/db_data"
    "/volume1/docker/m3u8-downloader/redis_data"
    "/volume1/docker/m3u8-downloader/logs"
    "/volume1/downloads/m3u8/completed"
    "/volume1/downloads/m3u8/processing"
    "/volume1/downloads/m3u8/failed"
)

for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "Creating $dir..."
        mkdir -p "$dir"
        chown 1026:100 "$dir"
        chmod 755 "$dir"
    fi
done

echo "✓ Directories checked"
echo ""

# Check Docker
echo "Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found!"
    echo "Please install Container Manager from Package Center"
    exit 1
fi
echo "✓ Docker found: $(docker --version)"
echo ""

# Pull images
echo "Pulling Docker images..."
docker-compose -f docker-compose.synology.yml pull

echo ""
echo "Building custom images..."
docker-compose -f docker-compose.synology.yml build

echo ""
echo "Starting services..."
docker-compose -f docker-compose.synology.yml up -d

echo ""
echo "Waiting for services to be ready..."
sleep 10

# Check service health
echo ""
echo "Checking service health..."

# Check database
if docker exec m3u8_db pg_isready -U postgres > /dev/null 2>&1; then
    echo "✓ Database is ready"
else
    echo "⚠ Database is not ready yet"
fi

# Check Redis
if docker exec m3u8_redis redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis is ready"
else
    echo "⚠ Redis is not ready yet"
fi

# Check API
if curl -f http://localhost:52052/api/health > /dev/null 2>&1; then
    echo "✓ API is ready"
else
    echo "⚠ API is not ready yet (might need more time)"
fi

echo ""
echo "========================================="
echo "Deployment complete!"
echo "========================================="
echo ""
echo "Services:"
echo "  - API: http://localhost:52052"
echo "  - Health check: http://localhost:52052/api/health"
echo "  - Database: localhost:5432"
echo "  - Redis: localhost:6379"
echo ""
echo "Next steps:"
echo "  1. Test API: curl http://localhost:52052/api/health"
echo "  2. Check logs: docker-compose -f docker-compose.synology.yml logs -f"
echo "  3. Install Chrome Extension"
echo "  4. Configure extension with:"
echo "     - NAS Endpoint: http://YOUR_NAS_IP:52052"
echo "     - API Key: (from .env file)"
echo ""
echo "To stop: docker-compose -f docker-compose.synology.yml down"
echo "To view logs: docker-compose -f docker-compose.synology.yml logs -f"
echo ""

