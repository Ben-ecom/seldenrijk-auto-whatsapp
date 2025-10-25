#!/bin/bash
# ============================================
# Production Startup Script for Railway
# Seldenrijk Auto WhatsApp System (Twilio)
# Version: 1.0.0 - Twilio Migration
# ============================================

set -e  # Exit on error

echo "=========================================="
echo "Seldenrijk Auto WhatsApp System (Twilio)"
echo "Version: 1.0.0"
echo "Environment: ${ENVIRONMENT:-production}"
echo "=========================================="

# ============ PRE-FLIGHT CHECKS ============

echo "Running pre-flight checks..."

# Check required environment variables
required_vars=(
    "TWILIO_ACCOUNT_SID"
    "TWILIO_AUTH_TOKEN"
    "TWILIO_WHATSAPP_NUMBER"
    "ANTHROPIC_API_KEY"
    "CHATWOOT_BASE_URL"
    "CHATWOOT_API_KEY"
    "CHATWOOT_ACCOUNT_ID"
)

# Optional but recommended variables
optional_vars=(
    "DATABASE_URL"
    "REDIS_URL"
    "SUPABASE_URL"
    "SUPABASE_KEY"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "ERROR: Required environment variable $var is not set"
        exit 1
    fi
done

echo "✅ All required environment variables present"

# Check optional variables
echo "Checking optional variables..."
for var in "${optional_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "⚠️  Optional variable $var is not set (recommended but not required)"
    else
        echo "✅ $var is set"
    fi
done

# ============ DATABASE CONNECTION CHECK ============

echo "Checking database connectivity..."

# Wait for PostgreSQL to be ready (if using DATABASE_URL)
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for PostgreSQL..."
    max_attempts=30
    attempt=0

    until psql "$DATABASE_URL" -c '\q' 2>/dev/null || [ $attempt -eq $max_attempts ]; do
        attempt=$((attempt + 1))
        echo "Attempt $attempt/$max_attempts: Waiting for PostgreSQL..."
        sleep 2
    done

    if [ $attempt -eq $max_attempts ]; then
        echo "WARNING: Could not connect to PostgreSQL after $max_attempts attempts"
        echo "Continuing anyway (using Supabase fallback)..."
    else
        echo "✅ PostgreSQL connection successful"
    fi
fi

# ============ REDIS CONNECTION CHECK ============

echo "Checking Redis connectivity..."

# Wait for Redis to be ready
max_attempts=30
attempt=0

until redis-cli -u "$REDIS_URL" ping 2>/dev/null || [ $attempt -eq $max_attempts ]; do
    attempt=$((attempt + 1))
    echo "Attempt $attempt/$max_attempts: Waiting for Redis..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "ERROR: Could not connect to Redis after $max_attempts attempts"
    echo "Redis is required for LangGraph checkpointing"
    exit 1
else
    echo "✅ Redis connection successful"
fi

# ============ DATABASE MIGRATIONS ============

# Run database migrations (if using Alembic)
# echo "Running database migrations..."
# alembic upgrade head
# echo "✅ Database migrations complete"

# ============ INITIALIZE APPLICATION ============

echo "Initializing application components..."

# Pre-compile Python bytecode for faster startup
python -m compileall -q app/

echo "✅ Application initialization complete"

# ============ START SERVICES ============

echo "=========================================="
echo "Starting FastAPI application..."
echo "Port: ${PORT:-8000}"
echo "Workers: ${WEB_CONCURRENCY:-4}"
echo "=========================================="

# Start Uvicorn with production settings
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-4} \
    --log-level ${LOG_LEVEL:-info} \
    --access-log \
    --no-use-colors \
    --proxy-headers \
    --forwarded-allow-ips="*"
