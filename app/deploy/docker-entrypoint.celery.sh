#!/usr/bin/env bash
set -euo pipefail   # crash on missing env variables, stop on any error, and exit if a pipe fails
set -x   # Enable verbose output for debugging

_term() {
  echo "Caught SIGTERM signal!"
  kill -TERM "$child" 2>/dev/null
}

trap _term SIGTERM

# Initialize celery worker
celery -A config beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler --detach
celery -A config worker -l info -Q default_priority,highest_priority,high_priority,low_priority &

child=$!
wait "$child"
