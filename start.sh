#!/bin/bash

# Railway startup script
# Railway provides the PORT environment variable

PORT=${PORT:-8000}

echo "Starting FastAPI application on port $PORT"

# Start the application with the Railway-provided port
exec python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT