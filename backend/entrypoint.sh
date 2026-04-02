#!/bin/sh
set -e

echo "Running database migrations..."
python -m alembic upgrade head

echo "Starting server..."
exec "$@"
