#!/bin/bash
# ============================================
# Smart Docker Rebuild with Cache Busting
# ============================================
#
# This script prevents Docker cache issues by:
# 1. Setting unique timestamp for each build
# 2. Forcing fresh deployment of application code
# 3. Preserving Python dependencies cache (for speed)
#
# Usage:
#   ./rebuild.sh                    # Build all services
#   ./rebuild.sh api celery-worker  # Build specific services
#

set -e  # Exit on error

# Generate unique cache bust timestamp
export CACHE_DATE=$(date +%s)

echo "🚀 Starting Docker rebuild with cache busting..."
echo "📅 Cache bust timestamp: $CACHE_DATE"
echo ""

# Build with cache bust argument
if [ $# -eq 0 ]; then
    echo "📦 Building ALL services..."
    docker-compose build --build-arg CACHE_DATE=$CACHE_DATE
else
    echo "📦 Building services: $@"
    docker-compose build --build-arg CACHE_DATE=$CACHE_DATE "$@"
fi

echo ""
echo "✅ Build complete! Restarting containers..."
docker-compose up -d --force-recreate

echo ""
echo "🎉 Rebuild successful! Fresh code deployed with timestamp: $CACHE_DATE"
echo ""
echo "📊 Next steps:"
echo "  - Check logs: docker-compose logs -f celery-worker"
echo "  - Test scraper: docker-compose exec api python -c 'from app.tasks.sync_inventory import sync_seldenrijk_inventory; sync_seldenrijk_inventory()'"
echo "  - Verify inventory: docker-compose exec celery-worker python -c 'from app.integrations.chatwoot_sync import get_redis_client; import json; print(json.loads(get_redis_client().get(\"seldenrijk:inventory:metadata\")))'"
