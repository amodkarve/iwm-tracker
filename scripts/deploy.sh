#!/bin/bash
# Deployment script for IWM Tracker to VPS
# Usage: ./deploy.sh

set -e  # Exit on error

# Configuration
VPS_HOST="amod@178.156.200.64"
VPS_DIR="~/iwm-tracker"
IMAGE_NAME="iwm-tracker"
IMAGE_TAG="latest"

echo "🚀 IWM Tracker Deployment Script"
echo "=================================="
echo ""

# Step 1: Build Docker image locally
echo "📦 Step 1: Building Docker image locally (AMD64 for VPS)..."
docker build --platform linux/amd64 -t ${IMAGE_NAME}:${IMAGE_TAG} .
echo "✅ Image built successfully"
echo ""

# Step 2: Save and compress image
echo "💾 Step 2: Saving and compressing image..."
docker save ${IMAGE_NAME}:${IMAGE_TAG} | gzip > ${IMAGE_NAME}.tar.gz
IMAGE_SIZE=$(du -h ${IMAGE_NAME}.tar.gz | cut -f1)
echo "✅ Image saved (${IMAGE_SIZE})"
echo ""

# Step 3: Transfer image to VPS
echo "📤 Step 3: Transferring image to VPS..."
scp ${IMAGE_NAME}.tar.gz ${VPS_HOST}:${VPS_DIR}/
echo "✅ Image transferred"
echo ""

# Step 4: Transfer configuration files
echo "📋 Step 4: Transferring configuration files..."
scp docker-compose.prod.yml ${VPS_HOST}:${VPS_DIR}/docker-compose.yml
scp -r .streamlit ${VPS_HOST}:${VPS_DIR}/
echo "✅ Configuration files transferred"
echo ""

# Step 5: Backup database and deploy on VPS
echo "🚀 Step 5: Backing up database and deploying on VPS..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ssh ${VPS_HOST} << ENDSSH
cd ~/iwm-tracker

# Create backup directory
mkdir -p data/backups

# Backup existing database if it exists
if [ -f data/wheel.db ]; then
    echo "💾 Backing up existing database..."
    cp data/wheel.db data/backups/wheel.db.${TIMESTAMP}
    echo "✅ Database backed up to data/backups/wheel.db.${TIMESTAMP}"
else
    echo "ℹ️  No existing database found - fresh deployment"
fi

# Load new image
echo "📦 Loading Docker image..."
docker load < iwm-tracker.tar.gz
rm iwm-tracker.tar.gz

# Create data directory if it doesn't exist
mkdir -p data

# Stop existing container (if any)
echo "🛑 Stopping existing container..."
docker-compose down 2>/dev/null || true

# Start new container
echo "🚀 Starting new container..."
docker-compose up -d

# Wait for health check
echo "⏳ Waiting for container to be healthy..."
sleep 5

# Verify container is running
if docker ps | grep -q iwm-tracker; then
    echo "✅ Container is running"
    docker ps | grep iwm-tracker
else
    echo "❌ Container failed to start"
    docker-compose logs --tail=30
    exit 1
fi

# Cleanup old backups (keep last 7 days)
echo "🧹 Cleaning up old backups (keeping last 7 days)..."
find data/backups -name 'wheel.db.*' -mtime +7 -delete 2>/dev/null || true

echo "✅ Deployment complete!"
ENDSSH

echo ""
echo "🎉 Deployment successful!"
echo ""
echo "Access your app at: https://iwmtracker.shrekllc.com"
echo ""

# Cleanup local compressed image
rm ${IMAGE_NAME}.tar.gz
echo "🧹 Cleaned up local files"
