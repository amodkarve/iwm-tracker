# Docker Setup for Wheel Tracker

This document explains how to run the Wheel Tracker application using Docker.

## Prerequisites

- Docker installed on your system
- Docker Compose (usually comes with Docker Desktop)

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository and navigate to the project directory:**
   ```bash
   cd iwm-tracker
   ```

2. **Run the application:**
   ```bash
   docker-compose up --build
   ```

3. **Access the application:**
   Open your browser and go to `http://localhost:8501`

### Using Docker directly

1. **Build the Docker image:**
   ```bash
   docker build -t wheel-tracker .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name wheel-tracker \
     -p 8501:8501 \
     -v $(pwd)/wheel.db:/app/wheel.db \
     -v $(pwd)/data:/app/data \
     wheel-tracker
   ```

3. **Access the application:**
   Open your browser and go to `http://localhost:8501`

## Configuration

### Custom Port

You can change the port the application runs on:

**Using Docker Compose:**
```bash
PORT=8080 docker-compose up --build
```

**Using Docker directly:**
```bash
docker run -d \
  --name wheel-tracker \
  -p 8080:8501 \
  -v $(pwd)/wheel.db:/app/wheel.db \
  -v $(pwd)/data:/app/data \
  -e STREAMLIT_SERVER_PORT=8501 \
  wheel-tracker
```

### Database Persistence

The database file (`wheel.db`) is mounted as a volume, so your data will persist between container restarts. The database file will be created in your project directory.

### Environment Variables

You can customize the application behavior using environment variables:

- `STREAMLIT_SERVER_PORT`: Port for the Streamlit server (default: 8501)
- `STREAMLIT_SERVER_ADDRESS`: Server address (default: 0.0.0.0)
- `STREAMLIT_SERVER_HEADLESS`: Run in headless mode (default: true)
- `STREAMLIT_SERVER_ENABLE_CORS`: Enable CORS (default: false)
- `STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION`: Enable XSRF protection (default: false)

## Management Commands

### Stop the application:
```bash
docker-compose down
```

### View logs:
```bash
docker-compose logs -f
```

### Restart the application:
```bash
docker-compose restart
```

### Remove the container and image:
```bash
docker-compose down --rmi all
```

## Troubleshooting

### Port already in use
If port 8501 is already in use, change the port:
```bash
PORT=8080 docker-compose up --build
```

### Database permissions
If you encounter database permission issues, ensure the database file is writable:
```bash
touch wheel.db
chmod 666 wheel.db
```

### Container won't start
Check the logs for errors:
```bash
docker-compose logs
```

## Development

For development, you can mount the source code as a volume to enable live reloading:

```bash
docker run -d \
  --name wheel-tracker-dev \
  -p 8501:8501 \
  -v $(pwd):/app \
  -v $(pwd)/wheel.db:/app/wheel.db \
  wheel-tracker
```

## Production Deployment

For production deployment, consider:

1. Using a reverse proxy (nginx, traefik)
2. Setting up SSL/TLS certificates
3. Using environment-specific configurations
4. Implementing proper logging and monitoring
5. Setting up database backups

Example production docker-compose.yml:
```yaml
version: '3.8'

services:
  wheel-tracker:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
      - ./wheel.db:/app/wheel.db
    environment:
      - STREAMLIT_SERVER_PORT=8501
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
      - STREAMLIT_SERVER_HEADLESS=true
      - STREAMLIT_SERVER_ENABLE_CORS=false
      - STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```
