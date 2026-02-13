#!/bin/sh
# Entrypoint script for containerized JiraHub
# Handles proper signal handling and initialization

export PYTHONPATH=/app
set -e

echo "Starting JiraHub container..."
echo "Running database migrations..."
alembic upgrade head || {
    echo "❌ Database migration failed!"
    exit 1
}

echo "✅ Migrations completed successfully"
echo "Starting Streamlit application on port 8501..."
exec streamlit run app/main.py
