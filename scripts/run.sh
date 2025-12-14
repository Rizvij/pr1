#!/usr/bin/env bash

# ProRyx Development Runner Script
# Usage: ./scripts/run.sh [command]

set -e

# Default config file
CONFIG_FILE="${CONFIG:-resources/config/local.yaml}"

case "$1" in
    "start" | "")
        echo "Starting ProRyx backend server..."
        CONFIG=$CONFIG_FILE uv run uvicorn proryx_backend.main:app --host 0.0.0.0 --port 8000 --reload
        ;;
    "start-prod")
        echo "Starting ProRyx in production mode..."
        CONFIG=resources/config/prod.yaml uv run uvicorn proryx_backend.main:app --host 0.0.0.0 --port 8000
        ;;
    "test")
        echo "Running tests..."
        uv run pytest -v
        ;;
    "test-cov")
        echo "Running tests with coverage..."
        uv run pytest -v --cov=proryx_backend --cov-report=html
        ;;
    "format")
        echo "Formatting code..."
        ./scripts/format.sh
        ;;
    "check")
        echo "Running quality checks..."
        ./scripts/check.sh
        ;;
    "logs")
        echo "Tailing application logs..."
        tail -f logs/app.log
        ;;
    "ui-dev")
        echo "Starting frontend development server..."
        cd ui/customer-app && npm run dev
        ;;
    "ui-build")
        echo "Building frontend for production..."
        cd ui/customer-app && npm run build
        ;;
    "install")
        echo "Installing dependencies..."
        uv sync
        cd ui/customer-app && npm install
        ;;
    "help" | "-h" | "--help")
        echo "ProRyx Development Runner"
        echo ""
        echo "Usage: ./scripts/run.sh [command]"
        echo ""
        echo "Commands:"
        echo "  start       Start backend server (default)"
        echo "  start-prod  Start in production mode"
        echo "  test        Run tests"
        echo "  test-cov    Run tests with coverage"
        echo "  format      Format code"
        echo "  check       Run quality checks"
        echo "  logs        Tail application logs"
        echo "  ui-dev      Start frontend dev server"
        echo "  ui-build    Build frontend for production"
        echo "  install     Install all dependencies"
        echo "  help        Show this help message"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run './scripts/run.sh help' for available commands"
        exit 1
        ;;
esac
