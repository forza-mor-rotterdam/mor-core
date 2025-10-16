#!/usr/bin/env bash
set -euo pipefail   # crash on missing env variables, stop on any error, and exit if a pipe fails
set -x   # Enable verbose output for debugging

rm -rf /static/*

# echo "Start with a fresh database"
# export PGPASSWORD=${DATABASE_PASSWORD}
# psql -h ${DATABASE_HOST_OVERRIDE} -p 5432 -d ${DATABASE_NAME} -U ${DATABASE_USER} -c "drop schema public cascade;"
# psql -h ${DATABASE_HOST_OVERRIDE} -p 5432 -d ${DATABASE_NAME} -U ${DATABASE_USER} -c "create schema public;"

# Log a message indicating the script has started
echo "Docker development entrypoint script has started."

# Apply database migrations
echo "Applying migrations..."
python manage.py migrate --noinput

# Create a superuser (if not already created)
echo "Creating superuser..."
if ! python manage.py createsuperuser --noinput; then
    echo "Superuser creation failed or already exists."
fi

# Create users for app to app communication
echo Create users
python manage.py createusers --noinput || true

# Create applicaties for app to app communication
echo Create applicaties
python manage.py create_applicaties

# Log a message indicating the script has completed
echo "Docker development entrypoint script has completed."

# Execute django runserver
exec python -m debugpy --listen 0.0.0.0:5678 /app/manage.py runserver 0.0.0.0:8000
