#!/bin/sh

# Wait for PostgreSQL
while ! nc -z db 5432; do
    echo "Waiting for PostgreSQL to start..."
    sleep 1
done

echo "PostgreSQL started"

# Wait for Redis
while ! nc -z redis 6379; do
    echo "Waiting for Redis to start..."
    sleep 1
done

echo "Redis started"

# Apply database migrations
alembic upgrade head

# Start FastAPI application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
