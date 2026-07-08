#!/bin/bash
set -e

# Start nginx in the background (serves the React SPA on port 8080)
# Overridden pid location to /tmp/nginx.pid so the non-root appuser can write it successfully
nginx -g "daemon off; pid /tmp/nginx.pid;" &
NGINX_PID=$!
echo "nginx started (PID: $NGINX_PID)"

# Start FastAPI/uvicorn backend in the foreground (keeps container alive)
echo "Starting Sampark AI backend on port 8000..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
