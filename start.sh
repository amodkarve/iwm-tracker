#!/bin/bash
# Quick start script for IWM Tracker

echo "🚀 Starting IWM Tracker with Docker Compose..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Build and start the container
echo "Building Docker image (this may take a few minutes on first run)..."
docker-compose up --build -d

# Wait for the app to be ready
echo ""
echo "Waiting for app to start..."
sleep 5

# Check if container is running
if docker-compose ps | grep -q "iwm-tracker"; then
    echo ""
    echo "✅ IWM Tracker is running!"
    echo ""
    echo "📊 Access the app at: http://localhost:8501"
    echo ""
    echo "Useful commands:"
    echo "  - View logs:     docker-compose logs -f"
    echo "  - Stop app:      docker-compose down"
    echo "  - Restart app:   docker-compose restart"
    echo "  - Rebuild:       docker-compose up --build -d"
    echo ""
else
    echo "❌ Failed to start. Check logs with: docker-compose logs"
    exit 1
fi
