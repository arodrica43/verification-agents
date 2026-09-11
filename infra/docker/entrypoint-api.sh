#!/bin/sh
set -eu
echo "Running Alembic migrations..."
cd /app/apps/api
alembic upgrade head
echo "Starting API..."
exec python -m formal_api.main
