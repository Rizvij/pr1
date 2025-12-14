#!/usr/bin/env bash

set -e
set -x

# Backend directories
APP="proryx_backend"
TESTS_DIR="proryx_backend/tests"

# Frontend directory
UI_DIR="ui/customer-app"

echo "Formatting Python code..."
find $APP -type f -name "*.py" | xargs uv run pyupgrade --py312-plus --keep-runtime-typing
if [ -d "$TESTS_DIR" ]; then
    find $TESTS_DIR -type f -name "*.py" | xargs uv run pyupgrade --py312-plus --keep-runtime-typing
fi
uv run ruff check --fix --select I $APP
uv run ruff format $APP

echo "Formatting Frontend code..."
if [ -d "$UI_DIR" ]; then
    cd $UI_DIR

    # Fix ESLint issues
    echo "Fixing ESLint issues..."
    npm run lint:fix

    # Format with Prettier
    echo "Formatting with Prettier..."
    npm run format

    cd ../..
else
    echo "Frontend directory not found, skipping frontend formatting"
fi

echo "All code formatting completed successfully!"
