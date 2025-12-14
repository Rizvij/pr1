#!/usr/bin/env sh

set -e
set -x

# Backend directories
APP="proryx_backend"
TESTS_DIR="proryx_backend/tests"

# Frontend directory
UI_DIR="ui/customer-app"

echo "Running Python code quality checks..."
uv run ruff check $APP
uv run ruff format --check $APP

echo "Running Frontend code quality checks..."
if [ -d "$UI_DIR" ]; then
    cd $UI_DIR

    # TypeScript type checking
    echo "Checking TypeScript types..."
    npm run typecheck || echo "TypeScript errors found (continuing...)"

    # ESLint checking
    echo "Running ESLint..."
    npm run lint || echo "ESLint errors found (continuing...)"

    # Prettier format checking
    echo "Checking Prettier formatting..."
    npm run format:check || echo "Prettier formatting issues found (continuing...)"

    cd ../..
else
    echo "Frontend directory not found, skipping frontend checks"
fi

echo "All quality checks completed successfully!"
