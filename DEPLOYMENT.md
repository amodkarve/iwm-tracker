# VPS Deployment Guide

## Quick Start

### 1. Cloudflare DNS Setup (Do This First!)

1. Log in to Cloudflare
2. Select `shrekllc.com` domain
3. Add DNS A record:
   - **Type**: `A`
   - **Name**: `iwmtracker`
   - **Content**: `178.156.200.64`
   - **Proxy status**: DNS only (⚫ gray cloud)
   - **TTL**: Auto

### 2. VPS Setup (One-Time)

SSH to your VPS and create the site with WordOps:

```bash
ssh amod@178.156.200.64

# Create directory
mkdir -p ~/iwm-tracker/data
cd ~/iwm-tracker

# Create WordOps site with reverse proxy
sudo wo site create iwmtracker.shrekllc.com --proxy=127.0.0.1:8501 --letsencrypt

# Copy .env file
nano .env
```

Add to `.env`:
```bash
MARKETDATA_API_TOKEN=your-token-here
WHEEL_DB_PATH=/app/data/wheel.db
```

### 3. Deploy Application

From your local machine:

```bash
# Make sure you're in the project directory
cd /Users/amod/antigravity/iwm-tracker

# Run deployment script
./deploy.sh
```

This will:
1. Build Docker image locally
2. Compress and transfer to VPS
3. Deploy with docker-compose
4. Start the application

### 4. Access Application

Open in browser:
```
https://iwmtracker.shrekllc.com
```

Login with:
- **Username**: `admin`
- **Password**: (the one in `.streamlit/secrets.toml`)

### 5. WebSocket Support (Crucial!)

Streamlit requires WebSocket support. If using WordOps/Nginx, ensure your configuration includes:

```nginx
location / {
    proxy_pass http://127.0.0.1:8501;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
    proxy_redirect off;
    include proxy_params;
}
```

To apply this on VPS:
```bash
ssh amod@178.156.200.64
sudo nano /etc/nginx/sites-available/iwmtracker.shrekllc.com
# Add the headers above
sudo systemctl reload nginx
```

---

## Manual Deployment (Alternative)

If you prefer manual control:

### Build Image
```bash
docker build -t iwm-tracker:latest .
docker save iwm-tracker:latest | gzip > iwm-tracker.tar.gz
```

### Transfer to VPS
```bash
scp iwm-tracker.tar.gz amod@178.156.200.64:~/iwm-tracker/
scp docker-compose.prod.yml amod@178.156.200.64:~/iwm-tracker/docker-compose.yml
scp -r .streamlit amod@178.156.200.64:~/iwm-tracker/
```

### Deploy on VPS
```bash
ssh amod@178.156.200.64
cd ~/iwm-tracker
docker load < iwm-tracker.tar.gz
docker-compose down
docker-compose up -d
docker-compose logs -f
```

---

## Updating the Application

To deploy updates:

```bash
./deploy.sh
```

Or manually:
```bash
# Build new image
docker build -t iwm-tracker:latest .
docker save iwm-tracker:latest | gzip > iwm-tracker.tar.gz

# Transfer and deploy
scp iwm-tracker.tar.gz amod@178.156.200.64:~/iwm-tracker/
ssh amod@178.156.200.64 "cd ~/iwm-tracker && docker load < iwm-tracker.tar.gz && docker-compose down && docker-compose up -d"
```

---

## Troubleshooting

### Check Container Status
```bash
ssh amod@178.156.200.64
docker ps | grep iwm-tracker
docker-compose logs --tail=50
```

### Check WordOps Site
```bash
sudo wo site info iwmtracker.shrekllc.com
sudo wo site list
```

### Check SSL Certificate
```bash
sudo certbot certificates
```

### Restart Container
```bash
cd ~/iwm-tracker
docker-compose restart
```

### View Live Logs
```bash
docker-compose logs -f
```

---

## Backup Database

```bash
ssh amod@178.156.200.64
cd ~/iwm-tracker
docker-compose exec iwm-tracker sqlite3 /app/data/wheel.db ".backup /app/data/wheel_backup_$(date +%Y%m%d).db"

# Download backup
scp amod@178.156.200.64:~/iwm-tracker/data/wheel_backup_*.db ./backups/
```

---

## Security Notes

- ✅ Password authentication enabled
- ✅ HTTPS via Let's Encrypt (WordOps)
- ✅ Port 8501 only exposed to localhost
- ✅ `.env` and `secrets.toml` excluded from git
- ✅ Database in persistent volume

---

## Port Configuration

- **8501**: Streamlit app (localhost only)
- **80/443**: Nginx reverse proxy (WordOps)

WordOps automatically handles:
- SSL certificate renewal
- HTTP to HTTPS redirect
- Reverse proxy to localhost:8501
