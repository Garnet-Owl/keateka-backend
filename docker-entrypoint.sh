#!/bin/sh
set -e

# Add application directory to Python path
export PYTHONPATH=$PYTHONPATH:/opt/pysetup

# Wait for postgres
until nc -z -v -w30 postgres 5432
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

# Initialize alembic if it hasn't been initialized
if [ ! -f "migrations/env.py" ]; then
    echo "Initializing alembic..."
    poetry run alembic init migrations
    # Copy our env.py over the default one
    cp app/migrations/env.py migrations/env.py
fi

# Run migrations
echo "Running database migrations..."
poetry run alembic upgrade head

# Start the application
echo "Starting FastAPI application..."
exec poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
