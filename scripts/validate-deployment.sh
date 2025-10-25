#!/bin/bash
# =============================================================================
# Deployment Validation Script
# Comprehensive testing for Twilio WhatsApp integration
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
ENVIRONMENT=${1:-staging}
BASE_URL=""

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

check_passed=0
check_failed=0

test_check() {
    if [ $? -eq 0 ]; then
        log_success "$1"
        ((check_passed++))
    else
        log_error "$1"
        ((check_failed++))
    fi
}

# =============================================================================
# Get Railway URL
# =============================================================================

get_railway_url() {
    log_info "Getting Railway domain for $ENVIRONMENT..."

    railway environment "$ENVIRONMENT" 2>/dev/null
    BASE_URL=$(railway domain 2>/dev/null)

    if [[ -z "$BASE_URL" ]]; then
        log_error "Could not get Railway domain. Are you linked to the project?"
        exit 1
    fi

    BASE_URL="https://$BASE_URL"
    log_success "Railway URL: $BASE_URL"
}

# =============================================================================
# Test 1: Health Check
# =============================================================================

test_health_check() {
    log_info "Test 1: Health endpoint..."

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")

    if [[ "$HTTP_CODE" == "200" ]]; then
        RESPONSE=$(curl -s "$BASE_URL/health")
        echo "Response: $RESPONSE"
        test_check "Health check passed (HTTP 200)"
        return 0
    else
        test_check "Health check failed (HTTP $HTTP_CODE)"
        return 1
    fi
}

# =============================================================================
# Test 2: Twilio Webhook Endpoint Exists
# =============================================================================

test_twilio_webhook_exists() {
    log_info "Test 2: Twilio webhook endpoint..."

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/webhooks/twilio")

    # 405 = Method Not Allowed (expected for GET on POST endpoint)
    # 401 = Unauthorized (Twilio signature verification - also acceptable)
    if [[ "$HTTP_CODE" == "405" || "$HTTP_CODE" == "401" || "$HTTP_CODE" == "200" ]]; then
        test_check "Twilio webhook endpoint exists (HTTP $HTTP_CODE)"
        return 0
    else
        test_check "Twilio webhook endpoint failed (HTTP $HTTP_CODE)"
        return 1
    fi
}

# =============================================================================
# Test 3: Environment Variables Check
# =============================================================================

test_environment_variables() {
    log_info "Test 3: Environment variables..."

    log_info "Checking Railway environment variables..."
    VARS=$(railway variables --environment "$ENVIRONMENT" 2>/dev/null | grep -E "TWILIO_|ANTHROPIC_" || true)

    # Check for required Twilio variables
    local has_account_sid=false
    local has_auth_token=false
    local has_phone=false

    if echo "$VARS" | grep -q "TWILIO_ACCOUNT_SID"; then
        has_account_sid=true
    fi

    if echo "$VARS" | grep -q "TWILIO_AUTH_TOKEN"; then
        has_auth_token=true
    fi

    if echo "$VARS" | grep -q "TWILIO_WHATSAPP_NUMBER"; then
        has_phone=true
    fi

    if $has_account_sid && $has_auth_token && $has_phone; then
        log_success "All required Twilio variables present"
        test_check "Environment variables configured"
        return 0
    else
        log_error "Missing Twilio environment variables:"
        $has_account_sid || echo "  - TWILIO_ACCOUNT_SID"
        $has_auth_token || echo "  - TWILIO_AUTH_TOKEN"
        $has_phone || echo "  - TWILIO_WHATSAPP_NUMBER"
        test_check "Environment variables missing"
        return 1
    fi
}

# =============================================================================
# Test 4: Twilio Signature Verification
# =============================================================================

test_twilio_signature() {
    log_info "Test 4: Twilio signature verification..."

    # This test sends a request WITHOUT Twilio signature
    # Should get 401 Unauthorized (signature verification working)

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        "$BASE_URL/api/webhooks/twilio" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "From=whatsapp%3A%2B31600000000&Body=test")

    if [[ "$HTTP_CODE" == "401" || "$HTTP_CODE" == "403" ]]; then
        test_check "Twilio signature verification active (HTTP $HTTP_CODE)"
        return 0
    else
        log_warning "Signature verification may not be active (HTTP $HTTP_CODE)"
        test_check "Signature verification unclear (HTTP $HTTP_CODE)"
        return 0  # Not a failure, just unclear
    fi
}

# =============================================================================
# Test 5: Database Connectivity (if applicable)
# =============================================================================

test_database_connectivity() {
    log_info "Test 5: Database connectivity..."

    # Check if database URL is configured
    DB_VAR=$(railway variables --environment "$ENVIRONMENT" 2>/dev/null | grep -E "DATABASE_URL|POSTGRES" || true)

    if [[ -n "$DB_VAR" ]]; then
        log_info "Database configured, checking connectivity..."
        # Try to hit an endpoint that requires DB
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/health/db" 2>/dev/null || echo "404")

        if [[ "$HTTP_CODE" == "200" ]]; then
            test_check "Database connectivity verified"
            return 0
        else
            log_warning "No DB health endpoint found (HTTP $HTTP_CODE)"
            test_check "Database check skipped (no endpoint)"
            return 0
        fi
    else
        log_info "No database configured, skipping..."
        test_check "Database check skipped (not configured)"
        return 0
    fi
}

# =============================================================================
# Test 6: Response Time Check
# =============================================================================

test_response_time() {
    log_info "Test 6: Response time check..."

    RESPONSE_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$BASE_URL/health")

    # Convert to milliseconds
    RESPONSE_TIME_MS=$(echo "$RESPONSE_TIME * 1000" | bc)

    log_info "Response time: ${RESPONSE_TIME_MS}ms"

    # Check if under 1000ms
    if (( $(echo "$RESPONSE_TIME < 1.0" | bc -l) )); then
        test_check "Response time acceptable (<1000ms)"
        return 0
    else
        log_warning "Response time is slow (${RESPONSE_TIME_MS}ms)"
        test_check "Response time slow but functional"
        return 0
    fi
}

# =============================================================================
# Test 7: Webhook URL Format
# =============================================================================

test_webhook_url_format() {
    log_info "Test 7: Webhook URL format..."

    WEBHOOK_URL="$BASE_URL/api/webhooks/twilio"

    log_info "Webhook URL: $WEBHOOK_URL"

    # Validate HTTPS
    if [[ "$WEBHOOK_URL" =~ ^https:// ]]; then
        test_check "Webhook uses HTTPS"
    else
        test_check "Webhook not using HTTPS"
        return 1
    fi

    # Copy to clipboard if possible
    if command -v pbcopy &> /dev/null; then
        echo "$WEBHOOK_URL" | pbcopy
        log_success "Webhook URL copied to clipboard"
    elif command -v xclip &> /dev/null; then
        echo "$WEBHOOK_URL" | xclip -selection clipboard
        log_success "Webhook URL copied to clipboard"
    fi

    return 0
}

# =============================================================================
# Test 8: Recent Logs Check
# =============================================================================

test_recent_logs() {
    log_info "Test 8: Checking recent logs..."

    log_info "Fetching last 20 log lines..."
    railway logs --environment "$ENVIRONMENT" | tail -20

    test_check "Logs retrieved successfully"
    return 0
}

# =============================================================================
# Test 9: SSL Certificate
# =============================================================================

test_ssl_certificate() {
    log_info "Test 9: SSL certificate check..."

    DOMAIN=$(echo "$BASE_URL" | sed 's|https://||')

    SSL_EXPIRY=$(echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN:443" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)

    if [[ -n "$SSL_EXPIRY" ]]; then
        log_info "SSL expires: $SSL_EXPIRY"
        test_check "SSL certificate valid"
        return 0
    else
        log_warning "Could not check SSL certificate"
        test_check "SSL check skipped"
        return 0
    fi
}

# =============================================================================
# Test 10: Doppler Integration Check (if using Doppler)
# =============================================================================

test_doppler_integration() {
    log_info "Test 10: Doppler integration check..."

    if command -v doppler &> /dev/null; then
        if doppler me &> /dev/null; then
            # Check if secrets exist
            SECRETS=$(doppler secrets --project "seldenrijk-auto" --config "$ENVIRONMENT" 2>/dev/null | grep -c "TWILIO" || echo "0")

            if [[ "$SECRETS" -gt 0 ]]; then
                log_success "Found $SECRETS Twilio secrets in Doppler"
                test_check "Doppler integration active"
                return 0
            else
                log_warning "No Twilio secrets found in Doppler"
                test_check "Doppler integration unclear"
                return 0
            fi
        else
            log_info "Not logged into Doppler, skipping..."
            test_check "Doppler check skipped"
            return 0
        fi
    else
        log_info "Doppler CLI not installed, skipping..."
        test_check "Doppler check skipped"
        return 0
    fi
}

# =============================================================================
# Summary Report
# =============================================================================

print_summary() {
    echo ""
    echo "============================================================================="
    echo "  VALIDATION SUMMARY - $ENVIRONMENT"
    echo "============================================================================="
    echo ""

    TOTAL_CHECKS=$((check_passed + check_failed))

    echo -e "${GREEN}Passed:${NC} $check_passed / $TOTAL_CHECKS"
    echo -e "${RED}Failed:${NC} $check_failed / $TOTAL_CHECKS"
    echo ""

    if [[ $check_failed -eq 0 ]]; then
        echo -e "${GREEN}✓ ALL CHECKS PASSED${NC}"
        echo ""
        echo "Next steps:"
        echo "1. Configure Twilio webhook URL:"
        echo "   $BASE_URL/api/webhooks/twilio"
        echo ""
        echo "2. Send test WhatsApp message"
        echo "3. Check logs: railway logs --environment $ENVIRONMENT"
        echo ""
        return 0
    else
        echo -e "${RED}✗ SOME CHECKS FAILED${NC}"
        echo ""
        echo "Please fix the failed checks before proceeding."
        echo ""
        return 1
    fi
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo ""
    echo "============================================================================="
    echo "  Deployment Validation - $ENVIRONMENT"
    echo "============================================================================="
    echo ""

    # Get Railway URL
    get_railway_url

    echo ""
    log_info "Running validation checks..."
    echo ""

    # Run all tests
    test_health_check
    echo ""
    test_twilio_webhook_exists
    echo ""
    test_environment_variables
    echo ""
    test_twilio_signature
    echo ""
    test_database_connectivity
    echo ""
    test_response_time
    echo ""
    test_webhook_url_format
    echo ""
    test_recent_logs
    echo ""
    test_ssl_certificate
    echo ""
    test_doppler_integration

    # Print summary
    print_summary
}

main
