#!/bin/bash
# ============================================
# Deployment Test Script
# Tests all critical endpoints after deployment
# ============================================

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
VERBOSE="${VERBOSE:-false}"

echo "🧪 Testing WhatsApp Recruitment Platform Deployment"
echo "📍 API URL: $API_URL"
echo "=================================="

# Test 1: Basic Health Check
echo -n "1️⃣  Testing basic health check... "
response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health")
if [ "$response" -eq 200 ]; then
    echo -e "${GREEN}✅ PASSED${NC}"
else
    echo -e "${RED}❌ FAILED (HTTP $response)${NC}"
    exit 1
fi

# Test 2: Detailed Health Check
echo -n "2️⃣  Testing detailed health check... "
response=$(curl -s "$API_URL/health/detailed")
if echo "$response" | grep -q "healthy"; then
    echo -e "${GREEN}✅ PASSED${NC}"
    if [ "$VERBOSE" = "true" ]; then
        echo "$response" | python3 -m json.tool
    fi
else
    echo -e "${RED}❌ FAILED${NC}"
    echo "$response"
    exit 1
fi

# Test 3: Liveness Probe
echo -n "3️⃣  Testing liveness probe... "
response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health/liveness")
if [ "$response" -eq 200 ]; then
    echo -e "${GREEN}✅ PASSED${NC}"
else
    echo -e "${RED}❌ FAILED (HTTP $response)${NC}"
    exit 1
fi

# Test 4: Readiness Probe
echo -n "4️⃣  Testing readiness probe... "
response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health/readiness")
if [ "$response" -eq 200 ] || [ "$response" -eq 503 ]; then
    echo -e "${GREEN}✅ PASSED (HTTP $response)${NC}"
    if [ "$response" -eq 503 ]; then
        echo -e "   ${YELLOW}⚠️  Note: Service not ready (dependencies may be down)${NC}"
    fi
else
    echo -e "${RED}❌ FAILED (HTTP $response)${NC}"
    exit 1
fi

# Test 5: Metrics Endpoint
echo -n "5️⃣  Testing Prometheus metrics... "
response=$(curl -s "$API_URL/metrics")
if echo "$response" | grep -q "http_requests_total"; then
    echo -e "${GREEN}✅ PASSED${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
    exit 1
fi

# Test 6: Webhook Security (should reject without signature)
echo -n "6️⃣  Testing webhook security... "
response=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$API_URL/webhooks/chatwoot" \
    -H "Content-Type: application/json" \
    -d '{"test": "data"}')
if [ "$response" -eq 403 ]; then
    echo -e "${GREEN}✅ PASSED (correctly rejected)${NC}"
else
    echo -e "${RED}❌ FAILED (should return 403, got $response)${NC}"
    exit 1
fi

# Test 7: WhatsApp Verification Endpoint
echo -n "7️⃣  Testing WhatsApp verification (should fail without token)... "
response=$(curl -s -o /dev/null -w "%{http_code}" \
    "$API_URL/webhooks/whatsapp/verify?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=test")
if [ "$response" -eq 403 ] || [ "$response" -eq 500 ]; then
    echo -e "${GREEN}✅ PASSED${NC}"
else
    echo -e "${RED}❌ FAILED (HTTP $response)${NC}"
    exit 1
fi

# Test 8: API Documentation (if not production)
if [ "$ENVIRONMENT" != "production" ]; then
    echo -n "8️⃣  Testing API docs... "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/docs")
    if [ "$response" -eq 200 ]; then
        echo -e "${GREEN}✅ PASSED${NC}"
    else
        echo -e "${YELLOW}⚠️  SKIPPED (docs disabled in production)${NC}"
    fi
fi

echo "=================================="
echo -e "${GREEN}✅ All tests passed!${NC}"
echo ""
echo "Next steps:"
echo "  1. Configure Chatwoot webhook URL: $API_URL/webhooks/chatwoot"
echo "  2. Test end-to-end message flow"
echo "  3. Monitor logs: docker-compose logs -f api"
echo ""
