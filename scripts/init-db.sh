#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Function to show usage
show_usage() {
    echo -e "${BLUE}ProRyx Database Initialization Script${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -c, --config PATH    Config file path (default: resources/config/local.yaml)"
    echo "  -r, --reset          Drop and recreate all tables (DESTRUCTIVE!)"
    echo "  -s, --seed           Seed initial data after migration"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Run migrations with default config"
    echo "  $0 -c resources/config/dev.yaml"
    echo "  $0 --reset                   # Reset database (drop all tables)"
    echo ""
}

# Default values
CONFIG_PATH="resources/config/local.yaml"
RESET_DB=false
SEED_DATA=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_PATH="$2"
            shift 2
            ;;
        -r|--reset)
            RESET_DB=true
            shift
            ;;
        -s|--seed)
            SEED_DATA=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# Validate config file exists
if [ ! -f "$CONFIG_PATH" ]; then
    echo -e "${RED}Error: Config file not found: $CONFIG_PATH${NC}"
    exit 1
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}ProRyx Database Initialization${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "Config: ${YELLOW}$CONFIG_PATH${NC}"
echo ""

# Export CONFIG for alembic
export CONFIG="$CONFIG_PATH"

# Reset database if requested
if [ "$RESET_DB" = true ]; then
    echo -e "${RED}⚠️  WARNING: This will DROP ALL TABLES and recreate them!${NC}"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo -e "${YELLOW}Aborted.${NC}"
        exit 0
    fi

    echo -e "${YELLOW}Downgrading to base...${NC}"
    uv run alembic downgrade base 2>/dev/null || echo -e "${YELLOW}No existing migrations to downgrade${NC}"
fi

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
uv run alembic upgrade head

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database migrations completed successfully!${NC}"
else
    echo -e "${RED}❌ Migration failed!${NC}"
    exit 1
fi

# Seed data if requested (initial admin account)
if [ "$SEED_DATA" = true ]; then
    echo -e "${YELLOW}Seeding initial data...${NC}"
    CONFIG="$CONFIG_PATH" uv run python -c "
import asyncio
from proryx_backend.database import AsyncSessionLocal
from proryx_backend.modules.auth.services import create_initial_admin
from proryx_backend.config import settings

async def seed():
    if not settings.init_admin_email:
        print('No initial admin configured in config. Skipping seed.')
        return

    async with AsyncSessionLocal() as session:
        try:
            await create_initial_admin(
                db=session,
                account_name=settings.init_account_name or 'Default Account',
                company_name=settings.init_company_name or 'Default Company',
                admin_email=settings.init_admin_email,
                admin_password=settings.init_admin_password or 'Admin123!',
                admin_first_name=settings.init_admin_first_name or 'Admin',
                admin_last_name=settings.init_admin_last_name,
            )
            print('Initial admin created successfully!')
        except Exception as e:
            print(f'Seed error (may already exist): {e}')

asyncio.run(seed())
"
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Database initialization complete!${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. Start the application: ${YELLOW}./build-and-integrate.sh ui-dev${NC}"
echo -e "  2. Access the API: ${YELLOW}http://localhost:8000/api/docs${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
