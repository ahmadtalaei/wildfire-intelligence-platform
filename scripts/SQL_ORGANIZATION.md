# SQL Scripts Organization

## Directory Structure and Purpose

### 📁 `scripts/database/` - **AUTO-EXECUTED** (Docker Initialization)
These SQL files are **automatically executed** when the PostgreSQL container starts for the first time.
They are mounted to `/docker-entrypoint-initdb.d/` in the container.

**Files that SHOULD be here:**
- ✅ `00_init_extensions.sql` - Initialize PostgreSQL extensions (PostGIS, UUID, etc.)
- ✅ `01_create_specialized_tables.sql` - Create all data source-specific tables
- ✅ `create_metadata_catalog.sql` - Create core metadata and catalog tables
- ✅ `add_dlq_and_spatial_extensions.sql` - Add Dead Letter Queue and spatial support
- ✅ `create_monitoring_tables.sql` - Create monitoring and metrics tables
- ✅ `create_challenge3_tables.sql` - Create Challenge 3 specific tables

**Execution Order:** Files run alphabetically (hence the 00_, 01_ prefixes)

### 📁 `scripts/database-samples/` - **MANUAL EXECUTION** (Sample Data)
These scripts populate tables with **sample/test data**. They should NOT run automatically.

**Files that should be here:**
- ❌ `populate_monitoring_data.sql` - Generates fake monitoring data for testing
- ❌ `add_recent_activity.sql` - Adds fake recent activity for dashboard testing

**Why not auto-run?**
- Contains fake/test data
- Would overwrite real production data
- Only needed for demos/testing
- Should be run manually when needed

### 📁 `scripts/database-migrations/` - **MANUAL EXECUTION** (Schema Updates)
For future schema migrations and updates that should be run manually or via migration tools.

**Files that might go here:**
- Schema version updates
- Column additions/modifications
- Index optimizations
- Data transformation scripts

### 📁 `scripts/database-manual/` - **MANUAL EXECUTION** (Maintenance)
For maintenance, cleanup, and administrative scripts.

**Files that might go here:**
- Database cleanup scripts
- Performance tuning scripts
- Backup/restore scripts
- Data export scripts

## Current File Classification

| File | Type | Should Auto-Run? | Reason |
|------|------|-----------------|---------|
| `00_init_extensions.sql` | Infrastructure | ✅ YES | Essential extensions needed at startup |
| `01_create_specialized_tables.sql` | Schema | ✅ YES | Core tables for data sources |
| `create_metadata_catalog.sql` | Schema | ✅ YES | Core application tables |
| `add_dlq_and_spatial_extensions.sql` | Schema | ✅ YES | Required functionality |
| `create_monitoring_tables.sql` | Schema | ✅ YES | Core monitoring infrastructure |
| `create_challenge3_tables.sql` | Schema | ✅ YES | Application-specific tables |
| `populate_monitoring_data.sql` | Sample Data | ❌ NO | Fake data for testing only |
| `add_recent_activity.sql` | Sample Data | ❌ NO | Fake recent activity for demos |

## How Docker Initialization Works

1. When PostgreSQL container starts for the **first time**:
   - Checks if database is already initialized
   - If not, runs all `*.sql` files in `/docker-entrypoint-initdb.d/`
   - Files run in alphabetical order
   - Runs as the database superuser

2. On subsequent restarts:
   - Scripts do NOT run again
   - Database persists via Docker volume

## Manual Execution Examples

### To load sample data for testing:
```bash
# Load monitoring sample data
docker exec -i wildfire-postgres psql -U wildfire_user -d wildfire_db < scripts/database-samples/populate_monitoring_data.sql

# Add recent activity
docker exec -i wildfire-postgres psql -U wildfire_user -d wildfire_db < scripts/database-samples/add_recent_activity.sql
```

### To run a migration:
```bash
docker exec -i wildfire-postgres psql -U wildfire_user -d wildfire_db < scripts/database-migrations/migration_v2.sql
```

## Best Practices

1. **Prefix with numbers** for execution order (00_, 01_, 02_)
2. **Use IF NOT EXISTS** to make scripts idempotent
3. **Never put test data** in auto-run directory
4. **Document each script** with clear headers
5. **Test locally** before adding to auto-run directory

## Impact of This Organization

### ✅ Benefits:
- Production database won't get polluted with test data
- Clear separation of concerns
- Predictable initialization behavior
- Safe for production deployments

### ⚠️ Important Notes:
- Only schema and infrastructure scripts auto-run
- Sample data must be loaded manually when needed
- Judges can choose to load sample data for testing