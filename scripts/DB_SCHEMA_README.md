# Database Schema Management

## Overview

The `init_db_schema.py` script provides centralized database schema management with two primary functions:

1. **`init_schema()`** - Initialize all database tables if they don't already exist
2. **`reset_database()`** - Purge all data from the database (with option to preserve users)

## Consolidated Tables

This script manages the following database tables:

### Core Tables
- **users** - User authentication and profile data
- **watchlists** - User-specific stock watchlists
- **user_watchlist** - Alternative watchlist table
- **stock_quotes** - Real-time stock market data
- **predictions** - Stock price predictions
- **model_configurations** - ML model configurations
- **STK** - Stock master data (scrip codes and company names)

### Indexes
- Optimized indexes for security_id, stock_symbol, user_id, and stock_status

## Usage

### 1. Initialize Schema (Safe Operation)

Initialize all tables if they don't exist. This is safe to run multiple times and won't affect existing data:

```bash
python scripts/init_db_schema.py --init
```

### 2. Initialize Schema and Load STK Data

Initialize schema and populate the STK table with stock master data:

```bash
python scripts/init_db_schema.py --init --load-stk
```

### 3. Reset Database (Preserve Users)

Purge all data from all tables EXCEPT the users table:

```bash
python scripts/init_db_schema.py --reset
```

You will be prompted for confirmation:
```
Are you sure you want to continue? (yes/no):
```

### 4. Reset Database (Delete Everything)

Purge ALL data including users table:

```bash
python scripts/init_db_schema.py --reset --no-preserve-users
```

⚠️ **WARNING**: This will delete ALL data including user accounts!

### 5. Custom Database Path

Use a custom database location:

```bash
python scripts/init_db_schema.py --init --db-path /path/to/custom.db
```

## Programmatic Usage

You can also use the script programmatically in your Python code:

```python
from scripts.init_db_schema import SchemaManager

# Create schema manager
schema_manager = SchemaManager()

# Initialize schema
schema_manager.init_schema()

# Load STK data
schema_manager.load_stk_data()

# Reset database (preserve users)
schema_manager.reset_database(preserve_users=True)

# Reset database (delete everything)
schema_manager.reset_database(preserve_users=False)
```

## Features

✅ **Safe Schema Initialization** - Won't overwrite existing data  
✅ **Selective Data Purging** - Option to preserve users table  
✅ **STK Data Loading** - Populate stock master data from stk.json  
✅ **Table Statistics** - Shows record counts after operations  
✅ **Transaction Safety** - All operations use transactions with rollback  
✅ **Comprehensive Indexes** - Optimized for query performance  
✅ **Interactive Confirmation** - Prevents accidental data loss  

## Table Schemas

### users
```sql
- id (INTEGER, PRIMARY KEY)
- username (TEXT, UNIQUE)
- password_hash (TEXT)
- email (TEXT, UNIQUE)
- created_at (TEXT)
- is_active (INTEGER)
- is_admin (INTEGER)
```

### stock_quotes
```sql
- id (INTEGER, PRIMARY KEY)
- company_name (TEXT)
- security_id (TEXT, UNIQUE)
- scrip_code (TEXT)
- stock_symbol (TEXT)
- current_value (REAL)
- change, p_change (REAL)
- day_high, day_low (REAL)
- ... and 15+ more fields
- stock_status (TEXT)
- download_attempts (INTEGER)
```

### predictions
```sql
- id (INTEGER, PRIMARY KEY)
- stock_symbol (TEXT)
- predicted_price (REAL)
- prediction_date (TEXT)
- user_id (INTEGER, FOREIGN KEY)
```

### STK (Stock Master Data)
```sql
- scrip_code (TEXT, PRIMARY KEY)
- company_name (TEXT)
```

## Safety Features

1. **Confirmation Required** - Reset operations require explicit "yes" confirmation
2. **User Preservation** - By default, users table is never deleted during reset
3. **Transaction Rollback** - Errors trigger automatic rollback
4. **Detailed Logging** - All operations print detailed status messages

## Examples

### Fresh Database Setup
```bash
# Create all tables and load stock master data
python scripts/init_db_schema.py --init --load-stk
```

### Development Reset
```bash
# Clear all data but keep user accounts
python scripts/init_db_schema.py --reset
```

### Complete Reset
```bash
# Nuclear option - delete everything
python scripts/init_db_schema.py --reset --no-preserve-users
```

## Migration from Old Scripts

This script consolidates functionality from:
- `create_db.py` - Basic table creation
- `load_stk_to_db.py` - STK data loading
- `migrate_schema.py` - Schema migrations
- `reset_db.py` - Database reset

You can now use a single script for all database management tasks.

