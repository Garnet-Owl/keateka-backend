#!/bin/sh
set -e

# Add application directory to Python path
export PYTHONPATH="$PYTHONPATH":/app

# Wait for postgres
until nc -z -v -w30 db 5432
do
  echo "Waiting for postgres database connection..."
  sleep 2
done
echo "Database is ready!"

# Wait for redis
until nc -z -v -w30 redis 6379
do
  echo "Waiting for redis connection..."
  sleep 2
done
echo "Redis is ready!"

# Run migrations
echo "Running database migrations..."
poetry run alembic upgrade head || {
    echo "Migration failed!"
    exit 1
}

# Start the application
echo "Starting FastAPI application..."
if [ "$RELOAD" = "True" ] || [ "$RELOAD" = "true" ]; then
    exec poetry run uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" --reload
else
    exec poetry run uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
fi
