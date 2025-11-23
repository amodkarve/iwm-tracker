# Migration Guide: Adding Config Table

This guide explains the automatic migration that adds the new `config` table required for portfolio NAV tracking.

## What Changed

A new `config` table has been added to store portfolio settings, specifically the starting portfolio value. The table structure is:

```sql
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## Automatic Migration on Startup

**✅ Migration happens automatically when the application starts!**

The database initialization code uses `CREATE TABLE IF NOT EXISTS`, which means:
- **New databases**: Automatically get the config table created
- **Existing databases**: The config table is automatically added on first app startup after the update
- **No data loss**: Existing tables and data are never modified or deleted
- **Idempotent**: Safe to run multiple times (won't duplicate tables)

When the FastAPI backend starts, it automatically:
1. Initializes the database connection
2. Creates any missing tables (including the new `config` table)
3. Preserves all existing data and tables

**No manual migration is required!** Just restart your application and the migration will happen automatically.

## Manual SQL Verification (Optional)

If you want to manually verify the migration, you can run SQL directly:

```bash
# Connect to the database
sqlite3 data/wheel.db

# Run the migration SQL (safe - won't modify existing data)
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

# Verify the table was created
.tables

# Exit
.quit
```

**Note**: This is not required since migration happens automatically on startup!

## VPS Deployment

### Automatic Migration (Recommended)

**The migration happens automatically when you restart the application!**

```bash
# SSH into your VPS
ssh user@your-vps

# Navigate to your project directory
cd /path/to/iwmtracker

# Pull latest code (if using git)
git pull

# Restart the application
docker-compose restart

# Or if running without Docker
# Restart your application server
```

The config table will be automatically created on startup. No manual steps required!

### Optional: Verify Migration

After restarting, you can verify the migration worked:

```bash
# Check that config table exists
sqlite3 data/wheel.db ".tables"

# Should show: cashflows  config  trades

# Check table structure
sqlite3 data/wheel.db ".schema config"
```

### Manual Migration (If Needed)

If you want to manually run the migration before restarting (optional):

## Verification

After migration, verify everything works:

1. **Check API endpoint**:
   ```bash
   curl http://localhost:8000/api/config/starting-portfolio-value
   ```
   Should return: `{"value": 1000000.0}` (default)

2. **Check NAV endpoint**:
   ```bash
   curl http://localhost:8000/api/analytics/portfolio-nav
   ```
   Should return NAV data with default starting value of $1M

3. **Set starting portfolio value** (optional):
   ```bash
   curl -X POST http://localhost:8000/api/config/starting-portfolio-value \
     -H "Content-Type: application/json" \
     -d '{"value": 1000000.0}'
   ```

## Rollback

If something goes wrong, restore from backup:

```bash
# Stop the application
docker-compose stop

# Restore database
cp data/wheel.db.backup_YYYYMMDD data/wheel.db

# Restart application
docker-compose start
```

## Safety Features

The migration script includes several safety features:

- ✅ **Automatic backup**: Creates a timestamped backup before migration
- ✅ **Idempotent**: Safe to run multiple times (won't duplicate tables)
- ✅ **Error handling**: Catches and reports errors clearly
- ✅ **Verification**: Checks if table already exists before creating

## Troubleshooting

### Error: "Database file not found"
- Check the database path is correct
- Ensure you have read/write permissions

### Error: "Permission denied"
- Check file permissions: `chmod 644 wheel.db`
- Ensure the user running the script has access

### Error: "Table already exists"
- This is not an error! The table already exists, migration not needed
- You can safely ignore this message

### Database locked
- Stop the application before migration
- Ensure no other process is using the database

## Questions?

If you encounter any issues during migration:
1. Check the backup was created successfully
2. Review the error message carefully
3. Verify database file permissions
4. Ensure the application is stopped during migration

