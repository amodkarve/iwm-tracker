#!/bin/bash
# Check if backend is running
# Usage: ./scripts/check_backend.sh

echo "Checking backend status..."
echo ""

# Check if running in Docker
if docker ps | grep -q "iwmtracker-backend"; then
    echo "✅ Backend container is running"
    docker ps | grep "iwmtracker-backend"
else
    echo "❌ Backend container is not running"
    echo ""
    echo "To start the backend:"
    echo "  docker-compose -f docker-compose.dev.yml up backend"
    echo ""
fi

# Check if backend is accessible
echo ""
echo "Testing backend connection..."
if curl -s http://localhost:8000/api/health > /dev/null; then
    echo "✅ Backend is accessible at http://localhost:8000"
else
    echo "❌ Backend is not accessible at http://localhost:8000"
fi

