#!/bin/bash
# =============================================================================
# End-to-End WhatsApp Testing Script
# Tests Twilio WhatsApp integration with real message scenarios
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

# =============================================================================
# Test Scenarios for Automotive Domain
# =============================================================================

TEST_SCENARIOS=(
    "Hallo, ik zoek een Volkswagen Golf"
    "Ik wil graag een auto kopen tussen 20k en 30k"
    "Heeft u een BMW 3-serie beschikbaar?"
    "Wat zijn de mogelijkheden voor financiering?"
    "Ik wil mijn oude auto inruilen"
    "Kan ik een afspraak maken voor een proefrit?"
    "Zoek een diesel SUV met automaat"
    "Heeft u elektrische auto's?"
    "Wat is de prijs van deze auto?"
    "Dank je wel, tot ziens"
)

# Expected intents for each scenario
EXPECTED_INTENTS=(
    "car_inquiry"
    "price_question"
    "car_inquiry"
    "financing_inquiry"
    "trade_in_inquiry"
    "appointment_request"
    "car_inquiry"
    "car_inquiry"
    "price_question"
    "general_inquiry"
)

# =============================================================================
# Instructions for Manual Testing
# =============================================================================

print_test_instructions() {
    echo ""
    echo "============================================================================="
    echo "  Manual WhatsApp E2E Testing Guide"
    echo "============================================================================="
    echo ""

    log_info "This script will guide you through testing the Twilio WhatsApp integration."
    echo ""

    log_warning "PREREQUISITES:"
    echo "1. You must have joined the Twilio Sandbox"
    echo "   - Go to: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn"
    echo "   - Send 'join <sandbox-word>' to your Twilio number"
    echo ""
    echo "2. Your webhook must be configured in Twilio:"
    railway environment "$ENVIRONMENT"
    WEBHOOK_URL="https://$(railway domain)/api/webhooks/twilio"
    echo "   - URL: $WEBHOOK_URL"
    echo "   - Method: POST"
    echo ""

    read -p "Press Enter when ready to start testing..."
}

# =============================================================================
# Monitor Railway Logs
# =============================================================================

monitor_logs() {
    log_info "Opening Railway logs in monitoring mode..."
    echo ""
    log_warning "Keep this terminal open to see real-time logs"
    echo "Press Ctrl+C to stop monitoring"
    echo ""

    railway environment "$ENVIRONMENT"
    railway logs --follow &
    LOG_PID=$!

    echo ""
    log_success "Monitoring logs (PID: $LOG_PID)"
    echo ""
}

# =============================================================================
# Interactive Testing Session
# =============================================================================

run_interactive_tests() {
    log_info "Starting interactive testing session..."
    echo ""

    local test_num=1
    local passed=0
    local failed=0

    for i in "${!TEST_SCENARIOS[@]}"; do
        SCENARIO="${TEST_SCENARIOS[$i]}"
        EXPECTED="${EXPECTED_INTENTS[$i]}"

        echo ""
        echo "─────────────────────────────────────────────────────────────────────────"
        log_info "Test $test_num/${#TEST_SCENARIOS[@]}: $EXPECTED"
        echo "─────────────────────────────────────────────────────────────────────────"
        echo ""

        echo "📱 Send this WhatsApp message:"
        echo ""
        echo -e "${YELLOW}$SCENARIO${NC}"
        echo ""

        log_warning "Expected behavior:"
        echo "  1. Message appears in Railway logs"
        echo "  2. Intent detected: $EXPECTED"
        echo "  3. Response sent back to WhatsApp"
        echo "  4. You receive response in WhatsApp"
        echo ""

        read -p "Did the test pass? (y/n/s=skip): " result

        case $result in
            y|Y)
                log_success "Test $test_num passed"
                ((passed++))
                ;;
            n|N)
                log_error "Test $test_num failed"
                ((failed++))
                echo ""
                read -p "Describe the issue: " issue
                echo "Issue: $issue" >> "test-failures-$(date +%Y%m%d-%H%M%S).log"
                ;;
            s|S)
                log_warning "Test $test_num skipped"
                ;;
        esac

        ((test_num++))
    done

    # Print summary
    echo ""
    echo "============================================================================="
    echo "  TEST SUMMARY"
    echo "============================================================================="
    echo ""

    TOTAL=$((passed + failed))
    echo -e "${GREEN}Passed:${NC} $passed / $TOTAL"
    echo -e "${RED}Failed:${NC} $failed / $TOTAL"

    if [[ $failed -eq 0 ]]; then
        echo ""
        log_success "🎉 All tests passed!"
    else
        echo ""
        log_error "Some tests failed. Check test-failures-*.log for details"
    fi

    echo ""
}

# =============================================================================
# Automated Monitoring (Check Logs for Errors)
# =============================================================================

check_for_errors() {
    log_info "Checking recent logs for errors..."

    railway environment "$ENVIRONMENT"
    RECENT_LOGS=$(railway logs 2>/dev/null | tail -50)

    # Check for common error patterns
    ERROR_COUNT=$(echo "$RECENT_LOGS" | grep -i "error\|exception\|failed\|traceback" | wc -l | tr -d ' ')

    if [[ "$ERROR_COUNT" -gt 0 ]]; then
        log_error "Found $ERROR_COUNT errors in recent logs:"
        echo ""
        echo "$RECENT_LOGS" | grep -i "error\|exception\|failed\|traceback" | head -10
        echo ""
        return 1
    else
        log_success "No errors found in recent logs"
        return 0
    fi
}

# =============================================================================
# Performance Metrics
# =============================================================================

check_performance() {
    log_info "Checking performance metrics..."

    railway environment "$ENVIRONMENT"

    # Get deployment info
    DEPLOYMENT_INFO=$(railway status 2>/dev/null || echo "Status unavailable")

    echo ""
    echo "$DEPLOYMENT_INFO"
    echo ""

    log_info "Checking response time..."
    WEBHOOK_URL="https://$(railway domain)/api/webhooks/twilio"

    # Test health endpoint response time
    HEALTH_URL="https://$(railway domain)/health"
    RESPONSE_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$HEALTH_URL" 2>/dev/null || echo "N/A")

    if [[ "$RESPONSE_TIME" != "N/A" ]]; then
        RESPONSE_MS=$(echo "$RESPONSE_TIME * 1000" | bc)
        log_info "Health endpoint response time: ${RESPONSE_MS}ms"

        if (( $(echo "$RESPONSE_TIME < 0.5" | bc -l) )); then
            log_success "Response time excellent (<500ms)"
        elif (( $(echo "$RESPONSE_TIME < 1.0" | bc -l) )); then
            log_success "Response time good (<1000ms)"
        else
            log_warning "Response time slow (>1000ms)"
        fi
    fi

    echo ""
}

# =============================================================================
# Message Flow Diagram
# =============================================================================

print_message_flow() {
    echo ""
    echo "============================================================================="
    echo "  Message Flow Diagram"
    echo "============================================================================="
    echo ""
    echo "  WhatsApp User"
    echo "       ↓"
    echo "  Twilio API"
    echo "       ↓"
    echo "  [Signature Verification]"
    echo "       ↓"
    echo "  Railway Webhook: /api/webhooks/twilio"
    echo "       ↓"
    echo "  TwilioWebhookRouter"
    echo "       ↓"
    echo "  ┌──────────────────────────────────┐"
    echo "  │   LangGraph State Machine        │"
    echo "  │   ├─ Router Agent                │"
    echo "  │   ├─ Extraction Agent            │"
    echo "  │   ├─ Conversation Agent          │"
    echo "  │   └─ CRM Agent (Chatwoot)        │"
    echo "  └──────────────────────────────────┘"
    echo "       ↓"
    echo "  TwilioService.send_message()"
    echo "       ↓"
    echo "  Twilio API"
    echo "       ↓"
    echo "  WhatsApp User"
    echo ""
}

# =============================================================================
# Test Data Generator
# =============================================================================

generate_test_data() {
    log_info "Generating test data for automated testing..."

    cat > "test-messages.json" <<EOF
{
  "test_scenarios": [
    {
      "id": 1,
      "message": "Hallo, ik zoek een Volkswagen Golf",
      "expected_intent": "car_inquiry",
      "expected_extraction": {
        "make": "Volkswagen",
        "model": "Golf"
      }
    },
    {
      "id": 2,
      "message": "Ik wil graag een auto kopen tussen 20k en 30k",
      "expected_intent": "price_question",
      "expected_extraction": {
        "min_price": 20000,
        "max_price": 30000
      }
    },
    {
      "id": 3,
      "message": "Heeft u een BMW 3-serie beschikbaar met automaat?",
      "expected_intent": "car_inquiry",
      "expected_extraction": {
        "make": "BMW",
        "model": "3-serie",
        "transmission": "automaat"
      }
    },
    {
      "id": 4,
      "message": "Wat zijn de mogelijkheden voor financiering?",
      "expected_intent": "financing_inquiry",
      "expected_extraction": {}
    },
    {
      "id": 5,
      "message": "Ik wil mijn oude auto inruilen",
      "expected_intent": "trade_in_inquiry",
      "expected_extraction": {}
    },
    {
      "id": 6,
      "message": "Kan ik een afspraak maken voor een proefrit?",
      "expected_intent": "appointment_request",
      "expected_extraction": {}
    },
    {
      "id": 7,
      "message": "Zoek een diesel SUV met automaat onder de 150000 km",
      "expected_intent": "car_inquiry",
      "expected_extraction": {
        "fuel_type": "diesel",
        "body_type": "SUV",
        "transmission": "automaat",
        "max_mileage": 150000
      }
    },
    {
      "id": 8,
      "message": "Heeft u elektrische auto's?",
      "expected_intent": "car_inquiry",
      "expected_extraction": {
        "fuel_type": "elektrisch"
      }
    },
    {
      "id": 9,
      "message": "Wat is de prijs van deze auto?",
      "expected_intent": "price_question",
      "expected_extraction": {}
    },
    {
      "id": 10,
      "message": "Dank je wel, tot ziens",
      "expected_intent": "general_inquiry",
      "expected_extraction": {}
    }
  ]
}
EOF

    log_success "Test data saved to test-messages.json"
    echo ""
}

# =============================================================================
# Troubleshooting Guide
# =============================================================================

print_troubleshooting() {
    echo ""
    echo "============================================================================="
    echo "  Troubleshooting Guide"
    echo "============================================================================="
    echo ""

    log_warning "Common Issues:"
    echo ""

    echo "1. No response received in WhatsApp"
    echo "   → Check webhook URL is configured in Twilio"
    echo "   → Check Railway logs for errors"
    echo "   → Verify Twilio credentials in environment variables"
    echo ""

    echo "2. 401 Unauthorized error"
    echo "   → Twilio signature verification failing"
    echo "   → Check TWILIO_AUTH_TOKEN is correct"
    echo "   → Verify webhook URL matches exactly (no trailing slash)"
    echo ""

    echo "3. 500 Internal Server Error"
    echo "   → Check Railway logs: railway logs --environment $ENVIRONMENT"
    echo "   → Check Anthropic API key is set"
    echo "   → Verify all required env vars are present"
    echo ""

    echo "4. Message received but wrong response"
    echo "   → Check Router Agent logs for intent detection"
    echo "   → Verify Extraction Agent is working correctly"
    echo "   → Check Conversation Agent prompts"
    echo ""

    echo "5. Slow response (>5 seconds)"
    echo "   → Check Anthropic API latency"
    echo "   → Verify Railway deployment region"
    echo "   → Check if cold start occurred"
    echo ""

    log_info "Debug commands:"
    echo "  railway logs --environment $ENVIRONMENT"
    echo "  railway status"
    echo "  railway variables"
    echo "  curl https://\$(railway domain)/health"
    echo ""
}

# =============================================================================
# Main Menu
# =============================================================================

show_menu() {
    echo ""
    echo "============================================================================="
    echo "  WhatsApp E2E Testing Menu - $ENVIRONMENT"
    echo "============================================================================="
    echo ""
    echo "1. View message flow diagram"
    echo "2. Run interactive testing session"
    echo "3. Monitor Railway logs"
    echo "4. Check for errors in logs"
    echo "5. Check performance metrics"
    echo "6. Generate test data (JSON)"
    echo "7. View troubleshooting guide"
    echo "8. Run full test suite (options 1-5)"
    echo "9. Exit"
    echo ""

    read -p "Select option (1-9): " choice

    case $choice in
        1)
            print_message_flow
            show_menu
            ;;
        2)
            print_test_instructions
            run_interactive_tests
            show_menu
            ;;
        3)
            monitor_logs
            show_menu
            ;;
        4)
            check_for_errors
            show_menu
            ;;
        5)
            check_performance
            show_menu
            ;;
        6)
            generate_test_data
            show_menu
            ;;
        7)
            print_troubleshooting
            show_menu
            ;;
        8)
            log_info "Running full test suite..."
            print_message_flow
            print_test_instructions
            check_for_errors
            check_performance
            run_interactive_tests
            show_menu
            ;;
        9)
            log_info "Exiting..."
            exit 0
            ;;
        *)
            log_error "Invalid option"
            show_menu
            ;;
    esac
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo ""
    echo "============================================================================="
    echo "  WhatsApp E2E Testing Tool"
    echo "  Environment: $ENVIRONMENT"
    echo "============================================================================="
    echo ""

    # Check if Railway CLI is available
    if ! command -v railway &> /dev/null; then
        log_error "Railway CLI not found. Please install it first:"
        echo "  brew install railway"
        exit 1
    fi

    # Show menu
    show_menu
}

main
