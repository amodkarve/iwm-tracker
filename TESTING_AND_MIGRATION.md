# Testing and Migration Guide

## Running Tests in Docker

### Quick Start

```bash
# Run all tests
./scripts/run_tests.sh

# Run specific test files
./scripts/run_tests.sh tests/test_portfolio.py tests/test_config_db.py -v

# Rebuild and run tests
./scripts/run_tests.sh --build tests/test_portfolio.py -v
```

### Manual Docker Commands

```bash
# Build test image
docker-compose -f docker-compose.test.yml build

# Run all tests
docker-compose -f docker-compose.test.yml run --rm test pytest -v

# Run specific tests
docker-compose -f docker-compose.test.yml run --rm test pytest tests/test_portfolio.py -v
docker-compose -f docker-compose.test.yml run --rm test pytest tests/test_config_db.py -v
docker-compose -f docker-compose.test.yml run --rm test pytest tests/test_portfolio_api.py -v

# Run with coverage
docker-compose -f docker-compose.test.yml run --rm test pytest --cov=src --cov-report=html -v
```

## New Test Files

### 1. `tests/test_portfolio.py`
Unit tests for portfolio PnL calculations:
- `TestClosedPnL`: 7 tests for closed (realized) PnL
- `TestOpenPnL`: 5 tests for open (unrealized) PnL  
- `TestNAV`: 5 tests for Net Asset Value calculations

### 2. `tests/test_config_db.py`
Unit tests for database config operations:
- `TestConfigDatabase`: 6 tests for config get/set operations

### 3. `tests/test_portfolio_api.py`
Integration tests for API endpoints:
- `TestConfigAPI`: 3 tests for config endpoints
- `TestPortfolioNavAPI`: 4 tests for portfolio NAV endpoint

## Database Migration

### Automatic Migration on Startup

**✅ Migration happens automatically when the application starts!**

The new `config` table is required for storing the starting portfolio value. The database initialization code automatically creates any missing tables (including the new `config` table) when the application starts.

**No manual migration is required!** Just restart your application and the migration will happen automatically.

- ✅ **New databases**: Automatically get the config table
- ✅ **Existing databases**: Config table is added automatically on first startup after update
- ✅ **No data loss**: Existing tables and data are never modified
- ✅ **Idempotent**: Safe to run multiple times

### Running Migration on VPS

**Migration happens automatically on application startup!**

#### Step 1: Restart Application

```bash
# SSH into VPS
ssh user@your-vps

# Navigate to project
cd /path/to/iwmtracker

# Pull latest code (if using git)
git pull

# Restart application
docker-compose restart
```

The config table will be automatically created on startup. No manual steps required!

#### Step 2: Verify Migration (Optional)

```bash
# Check table exists
sqlite3 data/wheel.db ".tables"
# Should show: cashflows  config  trades

# Check table structure
sqlite3 data/wheel.db ".schema config"
```

### Manual SQL Migration (Optional)

If you want to manually verify the migration (not required):

### Verification After Migration

1. **Check config endpoint**:
   ```bash
   curl http://localhost:8000/api/config/starting-portfolio-value
   ```
   Should return: `{"value": 1000000.0}`

2. **Check NAV endpoint**:
   ```bash
   curl http://localhost:8000/api/analytics/portfolio-nav
   ```
   Should return NAV data

3. **Set starting value** (optional):
   ```bash
   curl -X POST http://localhost:8000/api/config/starting-portfolio-value \
     -H "Content-Type: application/json" \
     -d '{"value": 1000000.0}'
   ```

## Rollback

If migration fails, restore from backup:

```bash
# Stop application
docker-compose stop

# Restore database
cp data/wheel.db.backup_YYYYMMDD data/wheel.db

# Restart
docker-compose start
```

## Troubleshooting

### Tests Fail in Docker

- Check Docker is running: `docker ps`
- Rebuild image: `docker-compose -f docker-compose.test.yml build --no-cache`
- Check Python path in container: `docker-compose -f docker-compose.test.yml run --rm test python --version`

### Migration Fails

- **Permission denied**: Check file permissions `chmod 644 wheel.db`
- **Database locked**: Stop application before migration
- **Table exists**: This is OK! Migration already completed

### Unicode Errors (Windows)

The migration script handles Windows encoding automatically. If you see encoding errors, ensure you're using Python 3.6+.

## Summary

- ✅ **Tests**: Run with `./scripts/run_tests.sh` or Docker commands
- ✅ **Migration**: Happens automatically on application startup
- ✅ **New DBs**: Automatically get config table (no migration needed)
- ✅ **Existing DBs**: Config table created automatically on first startup after update

