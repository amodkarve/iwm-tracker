#!/bin/bash
# Deployment script for IWM Tracker to VPS
# Usage: ./deploy.sh

set -e  # Exit on error

# Configuration
VPS_HOST="amod@178.156.200.64"
VPS_DIR="~/iwm-tracker"
BACKEND_IMAGE_NAME="iwm-tracker-backend"
FRONTEND_IMAGE_NAME="iwm-tracker-frontend"
IMAGE_TAG="latest"

echo "🚀 IWM Tracker Deployment Script"
echo "=================================="
echo ""

# Step 1: Build Docker images locally (AMD64 for VPS)
echo "📦 Step 1: Building Docker images locally (AMD64 for VPS)..."
echo "Building backend image..."
docker build --platform linux/amd64 -f Dockerfile.backend -t ${BACKEND_IMAGE_NAME}:${IMAGE_TAG} .
echo "✅ Backend image built successfully"
echo ""

echo "Building frontend image..."
docker build --platform linux/amd64 -f frontend/Dockerfile.prod -t ${FRONTEND_IMAGE_NAME}:${IMAGE_TAG} ./frontend
echo "✅ Frontend image built successfully"
echo ""

# Step 2: Save and compress images
echo "💾 Step 2: Saving and compressing images..."
echo "   This may take a few minutes for large images..."
echo "   Compressing backend image..."
docker save ${BACKEND_IMAGE_NAME}:${IMAGE_TAG} | gzip > ${BACKEND_IMAGE_NAME}.tar.gz
BACKEND_SIZE=$(du -h ${BACKEND_IMAGE_NAME}.tar.gz | cut -f1)
echo "   ✅ Backend image saved (${BACKEND_SIZE})"
echo "   Compressing frontend image..."
docker save ${FRONTEND_IMAGE_NAME}:${IMAGE_TAG} | gzip > ${FRONTEND_IMAGE_NAME}.tar.gz
FRONTEND_SIZE=$(du -h ${FRONTEND_IMAGE_NAME}.tar.gz | cut -f1)
echo "   ✅ Frontend image saved (${FRONTEND_SIZE})"
echo "✅ Images compressed successfully"
echo ""

# Step 3: Transfer images to VPS
echo "📤 Step 3: Transferring images to VPS..."
scp ${BACKEND_IMAGE_NAME}.tar.gz ${VPS_HOST}:${VPS_DIR}/
scp ${FRONTEND_IMAGE_NAME}.tar.gz ${VPS_HOST}:${VPS_DIR}/
echo "✅ Images transferred"
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

# Backup existing databases if they exist (both prod and test)
if [ -f data/wheel.db ]; then
    echo "💾 Backing up production database..."
    cp data/wheel.db data/backups/wheel.db.${TIMESTAMP}
    echo "✅ Production database backed up to data/backups/wheel.db.${TIMESTAMP}"
else
    echo "ℹ️  No existing production database found"
fi

if [ -f data/wheel_test.db ]; then
    echo "💾 Backing up test database..."
    cp data/wheel_test.db data/backups/wheel_test.db.${TIMESTAMP}
    echo "✅ Test database backed up to data/backups/wheel_test.db.${TIMESTAMP}"
else
    echo "ℹ️  No existing test database found"
fi

# Ensure data directory exists and has proper permissions
mkdir -p data
chmod 755 data

# Protect existing database files by ensuring they're not empty before deployment
if [ -f data/wheel.db ] && [ ! -s data/wheel.db ]; then
    echo "⚠️  WARNING: Production database exists but is empty. Restoring from backup if available..."
    LATEST_BACKUP=\$(ls -t data/backups/wheel.db.* 2>/dev/null | head -1)
    if [ -n "\$LATEST_BACKUP" ] && [ -s "\$LATEST_BACKUP" ]; then
        cp "\$LATEST_BACKUP" data/wheel.db
        echo "✅ Restored production database from backup"
    fi
fi

# Load new images
echo "📦 Loading Docker images..."
docker load < iwm-tracker-backend.tar.gz
docker load < iwm-tracker-frontend.tar.gz
rm iwm-tracker-backend.tar.gz iwm-tracker-frontend.tar.gz

# Stop existing containers (if any) - use down without -v to preserve volumes
echo "🛑 Stopping existing containers..."
docker-compose down --remove-orphans 2>/dev/null || true

# Also stop any containers that might be using the ports
echo "   Checking for containers using ports 8000 and 3000..."
docker ps --filter "publish=8000" --format "{{.ID}}" | xargs -r docker stop 2>/dev/null || true
docker ps --filter "publish=3000" --format "{{.ID}}" | xargs -r docker stop 2>/dev/null || true

# Remove any stopped containers with the same names
docker rm iwm-tracker-backend iwm-tracker-frontend iwm-tracker 2>/dev/null || true

# Verify databases still exist after container stop
if [ -f data/wheel.db ]; then
    DB_SIZE=\$(stat -f%z data/wheel.db 2>/dev/null || stat -c%s data/wheel.db 2>/dev/null || echo 0)
    echo "✅ Production database preserved (size: \${DB_SIZE} bytes)"
    # Try to set read-write permissions (may fail if owned by root, but that's OK)
    chmod 644 data/wheel.db 2>/dev/null || echo "   Note: Could not change permissions (may be owned by container user)"
fi

if [ -f data/wheel_test.db ]; then
    TEST_DB_SIZE=\$(stat -f%z data/wheel_test.db 2>/dev/null || stat -c%s data/wheel_test.db 2>/dev/null || echo 0)
    echo "✅ Test database preserved (size: \${TEST_DB_SIZE} bytes)"
    # Try to set read-write permissions (may fail if owned by root, but that's OK)
    chmod 644 data/wheel_test.db 2>/dev/null || echo "   Note: Could not change permissions (may be owned by container user)"
fi

# Start new container
echo "🚀 Starting new container..."
docker-compose up -d

# Verify databases still exist after container start
sleep 2
if [ -f data/wheel.db ]; then
    DB_SIZE_AFTER=\$(stat -f%z data/wheel.db 2>/dev/null || stat -c%s data/wheel.db 2>/dev/null || echo 0)
    if [ "\$DB_SIZE_AFTER" -gt 0 ]; then
        echo "✅ Production database verified after container start (size: \${DB_SIZE_AFTER} bytes)"
    else
        echo "⚠️  WARNING: Production database is empty after container start!"
    fi
fi

if [ -f data/wheel_test.db ]; then
    TEST_DB_SIZE_AFTER=\$(stat -f%z data/wheel_test.db 2>/dev/null || stat -c%s data/wheel_test.db 2>/dev/null || echo 0)
    if [ "\$TEST_DB_SIZE_AFTER" -gt 0 ]; then
        echo "✅ Test database verified after container start (size: \${TEST_DB_SIZE_AFTER} bytes)"
    else
        echo "⚠️  WARNING: Test database is empty after container start!"
    fi
fi

# Wait for health check
echo "⏳ Waiting for container to be healthy..."
sleep 5

# Verify containers are running
if docker ps | grep -q iwm-tracker-backend && docker ps | grep -q iwm-tracker-frontend; then
    echo "✅ Containers are running"
    docker ps | grep iwm-tracker
else
    echo "❌ Containers failed to start"
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

# Cleanup local compressed images
rm -f ${BACKEND_IMAGE_NAME}.tar.gz ${FRONTEND_IMAGE_NAME}.tar.gz
echo "🧹 Cleaned up local files"
