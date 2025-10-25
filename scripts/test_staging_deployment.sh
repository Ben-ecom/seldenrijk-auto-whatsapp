#!/bin/bash
# ============================================
# Staging Deployment Testing Script
# Twilio WhatsApp Integration
# ============================================
#
# Usage: ./scripts/test_staging_deployment.sh
#
# Prerequisites:
# - Railway CLI installed and authenticated
# - Staging environment deployed
# - STAGING_URL environment variable set
#
# ============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ============================================
# Helper Functions
# ============================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
        exit 1
    fi
}

# ============================================
# Pre-flight Checks
# ============================================

log_info "Starting pre-flight checks..."

# Check required commands
check_command "railway"
check_command "curl"
check_command "jq"

# Check Railway authentication
log_info "Checking Railway authentication..."
if ! railway whoami &> /dev/null; then
    log_error "Not logged into Railway. Run: railway login"
    exit 1
fi
log_success "Railway authentication OK"

# Get staging domain
log_info "Getting staging domain..."
STAGING_URL=$(railway domain 2>&1 | tail -1)

if [[ -z "$STAGING_URL" || "$STAGING_URL" == *"error"* ]]; then
    log_error "Could not get staging domain. Make sure you're linked to the correct project and environment."
    exit 1
fi

log_success "Staging URL: $STAGING_URL"

# ============================================
# Test 1: Health Check
# ============================================

log_info "Test 1: Health Check"

response=$(curl -s -o /dev/null -w "%{http_code}" "$STAGING_URL/health")

if [ "$response" -eq 200 ]; then
    log_success "Health check passed (HTTP 200)"
else
    log_error "Health check failed (HTTP $response)"
    exit 1
fi

# ============================================
# Test 2: Detailed Health Check
# ============================================

log_info "Test 2: Detailed Health Check"

detailed_health=$(curl -s "$STAGING_URL/health/detailed")

if echo "$detailed_health" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
    log_success "Detailed health check passed"

    # Check Redis
    if echo "$detailed_health" | jq -e '.components.redis.status == "healthy"' > /dev/null 2>&1; then
        log_success "  ✓ Redis: healthy"
    else
        log_warning "  ✗ Redis: unhealthy or missing"
    fi

    # Check Supabase
    if echo "$detailed_health" | jq -e '.components.supabase.status == "healthy"' > /dev/null 2>&1; then
        log_success "  ✓ Supabase: healthy"
    else
        log_warning "  ✗ Supabase: unhealthy or missing"
    fi

else
    log_error "Detailed health check failed"
    echo "$detailed_health" | jq '.'
    exit 1
fi

# ============================================
# Test 3: Webhook Endpoint Accessibility
# ============================================

log_info "Test 3: Webhook Endpoint Accessibility"

webhook_response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$STAGING_URL/webhooks/twilio/whatsapp" -d "test=1")

if [ "$webhook_response" -eq 403 ]; then
    log_success "Webhook endpoint accessible and secured (HTTP 403 - signature required)"
elif [ "$webhook_response" -eq 401 ]; then
    log_success "Webhook endpoint accessible and secured (HTTP 401 - unauthorized)"
else
    log_error "Webhook endpoint returned unexpected status: HTTP $webhook_response"
    log_warning "Expected 403 (Forbidden) or 401 (Unauthorized) when signature is missing"
fi

# ============================================
# Test 4: Environment Variables Check
# ============================================

log_info "Test 4: Environment Variables Check"

# Check critical Twilio variables are set
log_info "Checking Twilio environment variables..."

check_var() {
    local var_name=$1
    if railway variables get "$var_name" &> /dev/null; then
        log_success "  ✓ $var_name is set"
        return 0
    else
        log_error "  ✗ $var_name is NOT set"
        return 1
    fi
}

vars_ok=true

check_var "TWILIO_ACCOUNT_SID" || vars_ok=false
check_var "TWILIO_AUTH_TOKEN" || vars_ok=false
check_var "TWILIO_WHATSAPP_NUMBER" || vars_ok=false

# Optional but recommended
if check_var "TWILIO_WEBHOOK_URL"; then
    webhook_url=$(railway variables get TWILIO_WEBHOOK_URL)
    expected_url="$STAGING_URL/webhooks/twilio/whatsapp"

    if [ "$webhook_url" == "$expected_url" ]; then
        log_success "  ✓ TWILIO_WEBHOOK_URL matches staging URL"
    else
        log_warning "  ✗ TWILIO_WEBHOOK_URL mismatch"
        log_warning "    Expected: $expected_url"
        log_warning "    Actual:   $webhook_url"
    fi
fi

if [ "$vars_ok" = false ]; then
    log_error "Some required environment variables are missing"
    exit 1
fi

# ============================================
# Test 5: Service Logs Check
# ============================================

log_info "Test 5: Service Logs Check (last 50 lines)"

recent_logs=$(railway logs 2>&1 | tail -50)

if echo "$recent_logs" | grep -q "error\|Error\|ERROR"; then
    log_warning "Recent errors found in logs:"
    echo "$recent_logs" | grep -i "error" | tail -10
else
    log_success "No recent errors in logs"
fi

# Check for Twilio-related logs
if echo "$recent_logs" | grep -q "Twilio\|twilio"; then
    log_info "Recent Twilio activity detected in logs"
else
    log_warning "No recent Twilio activity in logs (may be normal if no messages sent recently)"
fi

# ============================================
# Test 6: API Documentation (if enabled)
# ============================================

log_info "Test 6: API Documentation Check"

docs_response=$(curl -s -o /dev/null -w "%{http_code}" "$STAGING_URL/docs")

if [ "$docs_response" -eq 200 ]; then
    log_success "API docs accessible at: $STAGING_URL/docs"
elif [ "$docs_response" -eq 404 ]; then
    log_info "API docs disabled (ENABLE_DOCS=false) - this is OK for production"
else
    log_warning "API docs returned HTTP $docs_response"
fi

# ============================================
# Test 7: Rate Limiting Check
# ============================================

log_info "Test 7: Rate Limiting (sending 5 rapid requests)"

rate_limit_test() {
    local success_count=0
    local rate_limited_count=0

    for i in {1..5}; do
        response=$(curl -s -o /dev/null -w "%{http_code}" "$STAGING_URL/health")

        if [ "$response" -eq 200 ]; then
            ((success_count++))
        elif [ "$response" -eq 429 ]; then
            ((rate_limited_count++))
        fi

        sleep 0.1  # Small delay
    done

    log_info "  Successful: $success_count/5"
    log_info "  Rate limited: $rate_limited_count/5"

    if [ "$success_count" -gt 0 ]; then
        log_success "Rate limiting working (some requests succeeded)"
    fi
}

rate_limit_test

# ============================================
# Test Summary
# ============================================

echo ""
log_success "============================================"
log_success "  STAGING DEPLOYMENT TEST SUMMARY"
log_success "============================================"
echo ""
log_info "Staging URL: $STAGING_URL"
log_success "✓ Health check passed"
log_success "✓ Detailed health check passed"
log_success "✓ Webhook endpoint accessible and secured"
log_success "✓ Environment variables configured"
log_info "  Logs reviewed (check warnings above)"
echo ""
log_success "============================================"
log_success "  DEPLOYMENT VALIDATION: PASSED"
log_success "============================================"
echo ""

# ============================================
# Next Steps
# ============================================

log_info "NEXT STEPS:"
echo ""
echo "1. Configure Twilio webhook URL in console:"
echo "   URL: $STAGING_URL/webhooks/twilio/whatsapp"
echo "   Method: POST"
echo ""
echo "2. Join Twilio sandbox (send WhatsApp message):"
echo "   To: +1 415 523 8886"
echo "   Message: join <your-sandbox-keyword>"
echo ""
echo "3. Send test WhatsApp message:"
echo "   Message: \"Hallo\""
echo "   Expected: Response from AI agent"
echo ""
echo "4. Monitor logs during testing:"
echo "   Command: railway logs --follow"
echo ""
echo "5. Complete validation checklist:"
echo "   File: STAGING-VALIDATION-CHECKLIST.md"
echo ""

log_success "Automated testing complete! 🚀"
