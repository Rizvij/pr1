# Development Setup and Commands

## Prerequisites

Before starting, ensure you have:
- **Python 3.12+**
- **Node.js 18+**
- **MySQL 8.0+**
- **[uv](https://github.com/astral-sh/uv)** - Python package manager

---

## First Time Setup

### 1. Clone and Install Dependencies

```bash
# Clone the repository
git clone <repository-url>
cd proryx

# Install Python dependencies
uv sync

# Install frontend dependencies
cd ui/customer-app && npm install && cd ../..
```

### 2. Create MySQL Database

The database must be created manually before running migrations:

```bash
mysql -u root -p
```

```sql
-- Create database
CREATE DATABASE db_proryx CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create development user (optional, can use root)
CREATE USER 'swm_dev'@'localhost' IDENTIFIED BY 'swm_dev_123';
GRANT ALL PRIVILEGES ON db_proryx.* TO 'swm_dev'@'localhost';
FLUSH PRIVILEGES;
```

### 3. Initialize Database with Migrations

```bash
# Run migrations and seed initial admin user
./scripts/init-db.sh --seed
```

### 4. Start the Application

```bash
# Start both backend and frontend
./build-and-integrate.sh ui-dev
```

---

## Database Initialization Script (init-db.sh)

The `init-db.sh` script handles database migrations and seeding.

### Basic Usage

```bash
./scripts/init-db.sh [options]
```

### Options

| Flag | Description |
|------|-------------|
| `-s, --seed` | Seed initial data (account, company, admin user) |
| `-r, --reset` | Drop all tables and recreate (DESTRUCTIVE!) |
| `-c, --config PATH` | Use custom config file (default: `resources/config/local.yaml`) |
| `-h, --help` | Show help message |

### Examples

```bash
# Run migrations only
./scripts/init-db.sh

# Run migrations and create initial admin
./scripts/init-db.sh --seed

# Reset database completely and reseed
./scripts/init-db.sh --reset --seed

# Use different config file
./scripts/init-db.sh --config resources/config/dev.yaml --seed
```

### What --seed Creates

Using values from `local.yaml`:
- **Account:** "Development Account"
- **Company:** "Dev Company"
- **Admin User:** admin@example.com / DevAdmin123!

---

## Development Scripts

### Available Scripts

| Script | Purpose |
|--------|---------|
| `./scripts/init-db.sh` | Database migrations and seeding |
| `./scripts/format.sh` | Auto-format Python and TypeScript code |
| `./scripts/check.sh` | Run linters and type checks |
| `./scripts/run.sh` | Start development server |
| `./build-and-integrate.sh` | Build and run full stack |

### Code Quality Commands

```bash
# Format all code (run before commits)
./scripts/format.sh

# Check for issues (must pass before commits)
./scripts/check.sh
```

---

## Starting the Application

### Option 1: Full Stack Development (Recommended)

```bash
./build-and-integrate.sh ui-dev
```

This starts:
- Backend on http://localhost:8000
- Frontend on http://localhost:3000

### Option 2: Backend Only

```bash
CONFIG=resources/config/local.yaml uv run uvicorn proryx_backend.main:app --reload --port 8000
```

### Option 3: Frontend Only

```bash
cd ui/customer-app
npm run dev
```

---

## Access URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000/api |
| API Docs (Swagger) | http://localhost:8000/api/docs |
| Health Check | http://localhost:8000/api/health |

---

## Login Credentials

### Development (local.yaml)

| Field | Value |
|-------|-------|
| Email | admin@example.com |
| Password | DevAdmin123! |

---

## Configuration Files

Located in `resources/config/`:

| File | Purpose |
|------|---------|
| `local.yaml` | Local development (hardcoded dev credentials) |
| `dev.yaml` | Development server (uses environment variables) |
| `prod.yaml` | Production (all secrets from environment) |

### Switching Configs

```bash
# Use different config
CONFIG=resources/config/dev.yaml ./scripts/init-db.sh

# Or export for session
export CONFIG=resources/config/dev.yaml
./scripts/init-db.sh
```

---

## Troubleshooting

### Database Connection Errors

**Problem:** `Can't connect to MySQL server`

**Solution:**
1. Ensure MySQL is running: `mysql.server start` (macOS) or `sudo systemctl start mysql` (Linux)
2. Verify database exists: `mysql -u root -p -e "SHOW DATABASES;"`
3. Check credentials in `resources/config/local.yaml`

### Migration Errors

**Problem:** `Target database is not up to date`

**Solution:**
```bash
# Check current migration status
CONFIG=resources/config/local.yaml uv run alembic current

# Upgrade to latest
CONFIG=resources/config/local.yaml uv run alembic upgrade head
```

### Port Already in Use

**Problem:** `Address already in use`

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'proryx_backend'`

**Solution:**
```bash
# Ensure you're in project root
cd /path/to/proryx

# Reinstall dependencies
uv sync
```

### CORS Errors

**Problem:** `Access-Control-Allow-Origin` errors in browser

**Solution:**
1. Check `cors_origins` in your config file
2. Ensure frontend URL is listed (http://localhost:3000)

### Frontend Build Errors

**Problem:** `npm install` fails

**Solution:**
```bash
cd ui/customer-app
rm -rf node_modules package-lock.json
npm install
```

---

## Development Workflow

### Before Committing

```bash
# 1. Format code
./scripts/format.sh

# 2. Run checks (must pass with 0 errors)
./scripts/check.sh

# 3. Test your changes manually
./build-and-integrate.sh ui-dev
```

### Creating Database Migrations

```bash
# Generate migration from model changes
CONFIG=resources/config/local.yaml uv run alembic revision --autogenerate -m "description"

# Apply migration
CONFIG=resources/config/local.yaml uv run alembic upgrade head
```

---

## Quick Reference

```bash
# Fresh start for new developer
uv sync
cd ui/customer-app && npm install && cd ../..
# Create MySQL database manually (see above)
./scripts/init-db.sh --seed
./build-and-integrate.sh ui-dev

# Daily development
./build-and-integrate.sh ui-dev

# Before committing
./scripts/format.sh && ./scripts/check.sh
```
