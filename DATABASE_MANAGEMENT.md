# Database Management Guide

## Overview

The IWM Tracker supports separate databases for **testing** and **production** to ensure you can safely develop and test changes without affecting your live trading data.

## Quick Start

### Production Database (Default)

```bash
# Use default production database
docker-compose up -d

# Or explicitly set it
WHEEL_DB_PATH=wheel.db docker-compose up -d
```

### Test Database

```bash
# Use test database
WHEEL_DB_PATH=wheel_test.db docker-compose up -d
```

## Configuration Methods

### Method 1: Environment Variable (Recommended)

Edit your `.env` file:

```bash
# For production
WHEEL_DB_PATH=wheel.db

# For testing
WHEEL_DB_PATH=wheel_test.db
```

Then restart:
```bash
docker-compose restart
```

### Method 2: Docker Compose Override

Create `docker-compose.override.yml`:

```yaml
version: '3.8'

services:
  wheel-tracker:
    environment:
      - WHEEL_DB_PATH=wheel_test.db
```

This file is git-ignored, so you can have different configs locally.

### Method 3: Command Line

```bash
# One-time test run
WHEEL_DB_PATH=wheel_test.db docker-compose up -d

# Switch back to production
WHEEL_DB_PATH=wheel.db docker-compose restart
```

## Workflow Examples

### Development Workflow

```bash
# 1. Start with test database
echo "WHEEL_DB_PATH=wheel_test.db" >> .env
docker-compose up -d

# 2. Test your changes, enter test trades
# Visit http://localhost:8501

# 3. When satisfied, switch to production
sed -i '' 's/wheel_test.db/wheel.db/' .env
docker-compose restart

# 4. Now using production data
```

### Testing New Features

```bash
# Use test database for experiments
WHEEL_DB_PATH=wheel_test.db docker-compose up -d

# Test the new feature
# Enter test trades, verify behavior

# Switch back to production when done
WHEEL_DB_PATH=wheel.db docker-compose restart
```

### Backup Before Testing

```bash
# Backup production database
cp wheel.db wheel_backup_$(date +%Y%m%d).db

# Test with a copy
cp wheel.db wheel_test.db
WHEEL_DB_PATH=wheel_test.db docker-compose restart

# If tests go well, keep changes
# If not, restore from backup
```

## Database Files

### Production
- **File**: `wheel.db`
- **Purpose**: Real trading data
- **Backup**: Regularly backup this file!

### Test
- **File**: `wheel_test.db` (or any name you choose)
- **Purpose**: Development and testing
- **Can delete**: Safe to delete and recreate

### Backups
- **Pattern**: `wheel_backup_YYYYMMDD.db`
- **Location**: Same directory as wheel.db
- **Frequency**: Before major changes

## Docker Volume Mounting

The database file is mounted from your host machine:

```yaml
volumes:
  - ./wheel.db:/app/wheel.db  # Production
  # or
  - ./wheel_test.db:/app/wheel.db  # Test
```

This means:
- ✅ Data persists between container restarts
- ✅ You can backup files directly from host
- ✅ You can inspect database with sqlite3 tools

## Switching Databases

### Current Database

Check which database is active:

```bash
docker exec iwm-tracker-wheel-tracker-1 printenv | grep WHEEL_DB_PATH
```

### Switch Without Downtime

```bash
# 1. Update .env file
echo "WHEEL_DB_PATH=wheel_test.db" > .env

# 2. Restart container
docker-compose restart

# 3. Verify
docker logs iwm-tracker-wheel-tracker-1 | grep -i database
```

## Best Practices

### 1. Always Use Test Database for Development

```bash
# In .env for development
WHEEL_DB_PATH=wheel_test.db
```

### 2. Backup Production Before Major Changes

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
cp wheel.db "backups/wheel_backup_${DATE}.db"
echo "Backed up to backups/wheel_backup_${DATE}.db"
```

### 3. Never Commit Database Files

Already in `.gitignore`:
```
wheel.db
wheel_test.db
wheel_backup_*.db
*.db
```

### 4. Document Your Database State

Keep notes on which database you're using:
```bash
# Add to your .env
WHEEL_DB_PATH=wheel_test.db
# NOTE: Testing new trade recommendation feature
```

## Troubleshooting

### Wrong Database Loaded

**Problem**: Seeing unexpected data

**Solution**:
```bash
# Check current database
docker exec iwm-tracker-wheel-tracker-1 printenv WHEEL_DB_PATH

# Verify file exists
ls -lah wheel*.db

# Check file size (should be >8KB if has data)
ls -lh wheel.db wheel_test.db
```

### Database Not Persisting

**Problem**: Data disappears after restart

**Solution**:
```bash
# Verify volume mount in docker-compose.yml
grep -A 5 "volumes:" docker-compose.yml

# Should see:
# - ./wheel.db:/app/wheel.db
```

### Permission Issues

**Problem**: Cannot write to database

**Solution**:
```bash
# Fix permissions
chmod 666 wheel.db wheel_test.db

# Restart container
docker-compose restart
```

## Advanced: Multiple Environments

### Setup

Create environment-specific configs:

```bash
# .env.production
WHEEL_DB_PATH=wheel.db
MARKETDATA_API_TOKEN=your_prod_token

# .env.test
WHEEL_DB_PATH=wheel_test.db
MARKETDATA_API_TOKEN=your_test_token

# .env.staging
WHEEL_DB_PATH=wheel_staging.db
MARKETDATA_API_TOKEN=your_staging_token
```

### Usage

```bash
# Load specific environment
cp .env.test .env
docker-compose restart

# Or use directly
docker-compose --env-file .env.test up -d
```

## Database Schema

Both databases use the same schema:

```sql
-- Trades table
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    side TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    strategy TEXT,
    expiration_date TEXT,
    strike_price REAL,
    option_type TEXT
);

-- Cashflows table
CREATE TABLE cashflows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    timestamp TEXT NOT NULL,
    description TEXT
);
```

## Migration Between Databases

### Copy Data from Test to Production

```bash
# Backup first!
cp wheel.db wheel_backup_$(date +%Y%m%d).db

# Copy specific trades
sqlite3 wheel_test.db ".dump trades" | sqlite3 wheel.db
```

### Merge Databases

```bash
# Export test data
sqlite3 wheel_test.db ".dump" > test_data.sql

# Import to production (careful!)
sqlite3 wheel.db < test_data.sql
```

## Summary

- **Production**: `WHEEL_DB_PATH=wheel.db` (default)
- **Testing**: `WHEEL_DB_PATH=wheel_test.db`
- **Switch**: Update `.env` and restart
- **Backup**: `cp wheel.db wheel_backup_$(date +%Y%m%d).db`
- **Verify**: `docker exec iwm-tracker-wheel-tracker-1 printenv WHEEL_DB_PATH`

This setup ensures you can safely develop and test without risking your production trading data!
