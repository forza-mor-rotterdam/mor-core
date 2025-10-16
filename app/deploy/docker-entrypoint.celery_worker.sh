#!/usr/bin/env bash
set -euo pipefail   # crash on missing env variables, stop on any error, and exit if a pipe fails
set -x   # Enable verbose output for debugging

_term() {
  echo "Caught SIGTERM signal!"
  kill -TERM "$child" 2>/dev/null
}

trap _term SIGTERM

# Initialize celery worker
celery -A config worker -l info &

child=$!
wait "$child"
