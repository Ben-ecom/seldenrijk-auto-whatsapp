#!/bin/bash
# =============================================================================
# AUTOMATED Railway Deployment (Non-Interactive)
# Seldenrijk Auto WhatsApp System (Twilio Migration)
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

echo ""
echo "============================================================================="
echo "  AUTOMATED Railway Deployment"
echo "  Using Railway API Token"
echo "============================================================================="
echo ""

# Check if Railway is already authenticated
if railway whoami &> /dev/null; then
    log_success "Railway already authenticated"
    railway whoami
else
    log_error "Railway not authenticated. You need to run: railway login"
    log_info "I cannot automate the login step (requires browser)"
    log_info ""
    log_info "Please run these 3 commands manually:"
    echo ""
    echo "1. railway login"
    echo "2. cd /Users/benomarlaamiri/Claude\ code\ project/seldenrijk-auto-whatsapp"
    echo "3. bash scripts/deploy-automated.sh"
    echo ""
    exit 1
fi

echo ""
log_info "Checking if project is linked..."

# Check if project is linked
if railway status &> /dev/null; then
    log_success "Project already linked"
else
    log_error "Project not linked"
    log_info "Run: railway link"
    exit 1
fi

echo ""
log_info "Setting Twilio environment variables..."

# Set Twilio variables (replace with your actual values)
railway variables set \
  TWILIO_ACCOUNT_SID="YOUR_TWILIO_ACCOUNT_SID" \
  TWILIO_API_KEY="YOUR_TWILIO_API_KEY_SID" \
  TWILIO_WHATSAPP_NUMBER="whatsapp:+YOUR_NUMBER"

log_success "Set public variables"

# Set sealed variables (secrets)
echo "YOUR_TWILIO_AUTH_TOKEN" | railway variables set TWILIO_AUTH_TOKEN --sealed
log_success "Set TWILIO_AUTH_TOKEN (sealed)"

echo "YOUR_TWILIO_API_SECRET" | railway variables set TWILIO_API_SECRET --sealed
log_success "Set TWILIO_API_SECRET (sealed)"

echo ""
log_info "All variables configured!"

# Show current variables (values hidden for sealed)
echo ""
log_info "Current variables:"
railway variables

echo ""
log_info "Starting deployment..."

# Deploy
railway up --detach

log_success "Deployment initiated!"

echo ""
log_info "Waiting for deployment to complete (30 seconds)..."
sleep 30

# Check status
railway status

echo ""
log_info "Getting webhook URL..."

DOMAIN=$(railway domain)

if [[ -n "$DOMAIN" ]]; then
    WEBHOOK_URL="https://$DOMAIN/api/webhooks/twilio"

    echo ""
    echo "============================================================================="
    log_success "Deployment Complete!"
    echo "============================================================================="
    echo ""
    echo "✅ Webhook URL: $WEBHOOK_URL"
    echo ""
    echo "📋 Next Step: Configure Twilio Webhook"
    echo ""
    echo "1. Go to: https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox"
    echo "2. In 'When a message comes in', paste:"
    echo "   $WEBHOOK_URL"
    echo "3. Method: POST"
    echo "4. Click Save"
    echo ""
else
    log_error "Could not retrieve domain"
    log_info "Get it manually with: railway domain"
fi

echo ""
log_success "🎉 Script complete!"
echo ""
