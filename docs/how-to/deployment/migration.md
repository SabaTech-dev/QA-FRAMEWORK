# Multi-Tenant Data Migration Guide

## Overview

This document describes the data migration process from single-tenant to multi-tenant architecture for the QA Framework. The migration script (`scripts/migrate_data.py`) handles the migration of existing data to a new multi-tenant system.

## Migration Architecture

### Components

The migration system consists of several key components:

1. **DataMigrator** - Base class for migration operations
2. **UserMigrator** - Handles user entity migration
3. **TestMigrator** - Handles test suite, case, and execution migration
4. **MigrationReportGenerator** - Generates comprehensive migration reports

### Database Schema Changes

The migration affects the following database models:

#### User Model
- **Previous**: `tenant_id` was nullable (could be NULL)
- **After**: All users will be assigned to the `default` tenant

#### Test Entities
- **TestSuite**, **TestCase**, **TestExecution**, **TestExecutionDetail**
- These entities will be migrated to the default tenant context
- Their foreign key relationships to users will be preserved (since users are already migrated)

#### Tenant Model
- **New**: `Tenant` entity for multi-tenant support
- **Default Tenant**: Created with slug `default`

## Migration Process

### Step 1: Create Default Tenant
The system creates a default tenant if it doesn't exist:
- **Name**: "Default Organization"
- **Slug**: `default`
- **Plan**: FREE
- **Status**: ACTIVE

### Step 2: Migrate Users
All users without a `tenant_id` are assigned to the default tenant:
- Users with existing `tenant_id` are left unchanged
- User IDs are tracked for reporting
- Errors are logged if migration fails

### Step 3: Migrate Tests
All test entities are migrated:
- **TestSuites** - Migrated with their metadata
- **TestCases** - Migrated with their configuration
- **TestExecutions** - Migrated preserving execution history
- **TestExecutionDetails** - Migrated with results and artifacts

### Step 4: Generate Report
A comprehensive report is generated including:
- Summary statistics
- Component-by-component breakdown
- Warnings and errors
- Recommendations

## Usage

### Running Migration

#### Dry Run (Recommended First)
Simulate the migration without making changes:

```bash
python scripts/migrate_data.py --dry-run
```

#### Live Migration
Execute the actual migration:

```bash
python scripts/migrate_data.py
```

#### With Verbose Logging
Enable detailed logging for debugging:

```bash
python scripts/migrate_data.py --verbose
```

#### Save Report to File
Generate a JSON report:

```bash
python scripts/migrate_data.py --output migration_report.json
```

### CLI Arguments

- `--dry-run`: Simulate migration without making changes
- `--output, -o`: Path to save migration report (JSON format)
- `--verbose, -v`: Enable verbose logging

## Migration Report

The migration report provides detailed information about the migration process:

### Report Sections

1. **Summary**
   - Overall status (completed, failed)
   - Execution time
   - Start and completion timestamps

2. **Records**
   - Total records processed
   - Successfully migrated records
   - Failed records

3. **By Component**
   - UserMigrator statistics
   - TestMigrator statistics

4. **Warnings**
   - Any warnings encountered during migration

5. **Errors**
   - Detailed error messages

6. **Recommendations**
   - Actionable recommendations based on migration results

### Report Output Example

```
================================================================================
MIGRATION REPORT
================================================================================

📊 SUMMARY
--------------------------------------------------------------------------------
Status: COMPLETED
Execution Time: 5.23s
Started: 2026-02-24T21:00:00
Completed: 2026-02-24T21:00:05

📈 RECORDS
--------------------------------------------------------------------------------
Total Records: 15
Migrated: 15
Failed: 0

🔧 BY COMPONENT
--------------------------------------------------------------------------------

USERMIGRATOR:
  Total: 10
  Migrated: 10
  Failed: 0

TESTMIGRATOR:
  Total: 5
  Migrated: 5
  Failed: 0

⚠️  WARNINGS
--------------------------------------------------------------------------------
1. Some users had conflicting data

💡 RECOMMENDATIONS
--------------------------------------------------------------------------------
1. Migration completed successfully. All data migrated to default tenant.
2. Verify data integrity by reviewing the details section below.
3. Consider setting up backup before production deployment.

================================================================================
```

## Pre-Migration Checklist

Before running the migration, ensure:

1. **Backup Database**
   ```bash
   pg_dump $DATABASE_URL > backup_before_migration.sql
   ```

2. **Verify Environment**
   - Ensure database connection is working
   - Verify write permissions for all tables
   - Check disk space for report storage

3. **Review Existing Data**
   - Check number of users
   - Check number of test suites and cases
   - Identify any data integrity issues

4. **Test Environment**
   - Run migration in staging environment first
   - Verify results in staging database
   - Test data integrity after migration

## Post-Migration Verification

After running the migration:

1. **Check Database**
   - Verify default tenant exists
   - Confirm all users have `tenant_id` set
   - Validate test entities are properly migrated

2. **Verify Application**
   - Test user login
   - Verify test execution
   - Check dashboard functionality

3. **Review Report**
   - Check for any errors or warnings
   - Review recommendations
   - Validate statistics

## Common Issues and Solutions

### Issue: Permission Denied

**Symptoms**: Migration fails with "permission denied" errors

**Solution**:
```bash
# Grant write permissions
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;"
```

### Issue: Tenant Already Exists

**Symptoms**: "Default tenant already exists"

**Solution**: This is normal. The migration will skip creating a new tenant and use the existing one.

### Issue: Database Connection Failed

**Symptoms**: "Connection to database failed"

**Solution**:
```bash
# Check database connection
psql $DATABASE_URL -c "SELECT 1;"

# Verify DATABASE_URL in config
cat config/settings.py | grep DATABASE_URL
```

### Issue: Data Integrity Errors

**Symptoms**: Some records show as failed

**Solution**:
1. Check the error section of the migration report
2. Review specific errors
3. Consider manual data correction if needed
4. Retry migration after fixing issues

## Rollback Procedure

If migration causes issues:

1. **Restore Database**
   ```bash
   psql $DATABASE_URL < backup_before_migration.sql
   ```

2. **Revert Code**
   - Revert to previous version
   - Or implement rollback logic in application code

3. **Verify System**
   - Confirm system is back to working state
   - Test critical functionality

## Best Practices

1. **Always Test First**
   - Run migration with `--dry-run` first
   - Review report before live migration

2. **Backup Before Migration**
   - Always have a working backup before proceeding
   - Store backup in secure location

3. **Run During Low Traffic**
   - Schedule migration during off-peak hours
   - Consider database maintenance windows

4. **Monitor Performance**
   - Use `--verbose` flag during initial runs
   - Monitor database performance during migration
   - Consider database indexes if migration is slow

5. **Validate After Migration**
   - Run application tests after migration
   - Verify user data and test entities
   - Check dashboard functionality

## Technical Details

### Migration Files

- **Migrator**: `src/infrastructure/migration/migrator.py`
- **User Migrator**: `src/infrastructure/migration/user_migrator.py`
- **Test Migrator**: `src/infrastructure/migration/test_migrator.py`
- **Report Generator**: `src/infrastructure/migration/report_generator.py`
- **CLI Script**: `scripts/migrate_data.py`
- **Unit Tests**: `tests/unit/infrastructure/test_migration.py`

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  CLI Script                             │
│            (scripts/migrate_data.py)                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   Migration Orchestrator                │
│                   (DataMigrator)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ UserMigrator │  │TestMigrator  │  │ ReportGen    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Database (PostgreSQL)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │   User   │  │ TestSuite│  │    MigrationReport   │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Multi-Tenant Strategy

1. **Default Tenant**: All existing data is assigned to the `default` tenant
2. **Tenant Isolation**: Users and tests are properly scoped to their tenant
3. **Backward Compatibility**: Existing application code continues to work
4. **Future Scalability**: Ready for adding new tenants in the future

## Performance Considerations

### Migration Time

Expected migration time:
- **Small System** (<100 users, <100 test cases): 1-2 minutes
- **Medium System** (100-1000 users, 100-1000 test cases): 5-10 minutes
- **Large System** (>1000 users, >1000 test cases): 10-30 minutes

### Optimization Tips

1. **Disable Indexes**: Temporarily drop indexes during migration
2. **Batch Processing**: Process records in batches if needed
3. **Parallel Migrations**: Run migrations for different components in parallel
4. **Database Tuning**: Increase PostgreSQL `work_mem` if needed

## Support and Troubleshooting

For issues or questions:
1. Check the migration report for detailed errors
2. Review this document for common solutions
3. Enable verbose logging for detailed debugging
4. Contact the development team with detailed error messages

## Version History

- **v1.0** (2026-02-24): Initial migration system implementation
  - Multi-tenant data migration
  - Comprehensive reporting
  - Dry-run support
  - Unit tests
