#!/bin/bash
# =============================================================================
# Simple Railway Deployment - No External Tools Needed
# Seldenrijk Auto WhatsApp System (Twilio Migration)
# =============================================================================
# Total time: ~5 minutes
# Requirements: Railway CLI only
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

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

echo ""
echo "============================================================================="
echo "  Railway Sealed Variables Deployment"
echo "  Seldenrijk Auto WhatsApp System (Twilio)"
echo "============================================================================="
echo ""

# =============================================================================
# Step 1: Check Railway CLI
# =============================================================================

log_info "Step 1: Checking Railway CLI..."

if ! command -v railway &> /dev/null; then
    log_error "Railway CLI not found"
    echo ""
    log_info "Installing Railway CLI..."

    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install railway
    else
        curl -fsSL https://railway.app/install.sh | sh
    fi

    log_success "Railway CLI installed"
else
    log_success "Railway CLI found"
fi

echo ""

# =============================================================================
# Step 2: Railway Login
# =============================================================================

log_info "Step 2: Railway authentication..."

if railway whoami &> /dev/null; then
    log_success "Already logged in to Railway"
    railway whoami
else
    log_warning "Not logged in. Opening browser..."
    railway login

    if railway whoami &> /dev/null; then
        log_success "Login successful"
    else
        log_error "Login failed"
        exit 1
    fi
fi

echo ""

# =============================================================================
# Step 3: Link Project
# =============================================================================

log_info "Step 3: Linking Railway project..."

if railway status &> /dev/null; then
    log_success "Already linked to project"
    railway status
else
    log_warning "Project not linked. Linking now..."
    railway link

    if railway status &> /dev/null; then
        log_success "Project linked successfully"
    else
        log_error "Failed to link project"
        exit 1
    fi
fi

echo ""

# =============================================================================
# Step 4: Select Environment
# =============================================================================

log_info "Step 4: Selecting staging environment..."

# List available environments
log_info "Available environments:"
railway environment

echo ""
read -p "Enter environment name (default: staging): " ENV_NAME
ENV_NAME=${ENV_NAME:-staging}

# Switch to environment
railway environment use "$ENV_NAME"
log_success "Using environment: $ENV_NAME"

echo ""

# =============================================================================
# Step 5: Collect Twilio Credentials
# =============================================================================

log_warning "Step 5: Enter your Twilio credentials"
echo ""
echo "You'll need:"
echo "1. Twilio Account SID (starts with AC...)"
echo "2. Twilio Auth Token (32 characters)"
echo "3. Twilio WhatsApp Phone Number (format: whatsapp:+31...)"
echo ""

# Prompt for credentials
read -p "Twilio Account SID: " TWILIO_ACCOUNT_SID
read -sp "Twilio Auth Token: " TWILIO_AUTH_TOKEN
echo ""
read -p "Twilio WhatsApp Number (whatsapp:+31...): " TWILIO_WHATSAPP_NUMBER

# Validate Account SID
if [[ ! $TWILIO_ACCOUNT_SID =~ ^AC[a-f0-9]{32}$ ]]; then
    log_error "Invalid Account SID format (should start with AC and be 34 characters)"
    exit 1
fi

# Validate Auth Token
if [[ -z "$TWILIO_AUTH_TOKEN" ]]; then
    log_error "Auth Token cannot be empty"
    exit 1
fi

# Validate WhatsApp number
if [[ ! $TWILIO_WHATSAPP_NUMBER =~ ^whatsapp:\+ ]]; then
    log_error "Invalid WhatsApp number format (should start with 'whatsapp:+')"
    exit 1
fi

log_success "Credentials validated"

echo ""

# =============================================================================
# Step 6: Set Railway Variables (SEALED)
# =============================================================================

log_info "Step 6: Setting Railway environment variables..."

# Set Twilio variables (SEALED = never visible in UI)
echo "$TWILIO_ACCOUNT_SID" | railway variables set TWILIO_ACCOUNT_SID --sealed
log_success "Set TWILIO_ACCOUNT_SID (sealed)"

echo "$TWILIO_AUTH_TOKEN" | railway variables set TWILIO_AUTH_TOKEN --sealed
log_success "Set TWILIO_AUTH_TOKEN (sealed)"

echo "$TWILIO_WHATSAPP_NUMBER" | railway variables set TWILIO_WHATSAPP_NUMBER
log_success "Set TWILIO_WHATSAPP_NUMBER"

# Ask for other credentials
echo ""
log_info "Other required credentials..."

# Anthropic API Key
if railway variables get ANTHROPIC_API_KEY &> /dev/null; then
    log_success "ANTHROPIC_API_KEY already set"
else
    echo ""
    read -sp "Anthropic API Key (sk-ant-...): " ANTHROPIC_API_KEY
    echo ""
    if [[ -n "$ANTHROPIC_API_KEY" ]]; then
        echo "$ANTHROPIC_API_KEY" | railway variables set ANTHROPIC_API_KEY --sealed
        log_success "Set ANTHROPIC_API_KEY (sealed)"
    fi
fi

# Chatwoot credentials
if railway variables get CHATWOOT_API_KEY &> /dev/null; then
    log_success "CHATWOOT_API_KEY already set"
else
    echo ""
    read -sp "Chatwoot API Key: " CHATWOOT_API_KEY
    echo ""
    if [[ -n "$CHATWOOT_API_KEY" ]]; then
        echo "$CHATWOOT_API_KEY" | railway variables set CHATWOOT_API_KEY --sealed
        log_success "Set CHATWOOT_API_KEY (sealed)"
    fi
fi

if railway variables get CHATWOOT_BASE_URL &> /dev/null; then
    log_success "CHATWOOT_BASE_URL already set"
else
    read -p "Chatwoot Base URL (https://app.chatwoot.com): " CHATWOOT_BASE_URL
    CHATWOOT_BASE_URL=${CHATWOOT_BASE_URL:-https://app.chatwoot.com}
    railway variables set CHATWOOT_BASE_URL="$CHATWOOT_BASE_URL"
    log_success "Set CHATWOOT_BASE_URL"
fi

if railway variables get CHATWOOT_ACCOUNT_ID &> /dev/null; then
    log_success "CHATWOOT_ACCOUNT_ID already set"
else
    read -p "Chatwoot Account ID: " CHATWOOT_ACCOUNT_ID
    if [[ -n "$CHATWOOT_ACCOUNT_ID" ]]; then
        railway variables set CHATWOOT_ACCOUNT_ID="$CHATWOOT_ACCOUNT_ID"
        log_success "Set CHATWOOT_ACCOUNT_ID"
    fi
fi

echo ""
log_success "All variables configured"

# Show variables (values hidden for sealed vars)
echo ""
log_info "Current variables:"
railway variables

echo ""

# =============================================================================
# Step 7: Deploy to Railway
# =============================================================================

log_info "Step 7: Deploying to Railway..."
echo ""

railway up

log_success "Deployment initiated"

echo ""
log_info "Waiting for deployment to complete (30 seconds)..."
sleep 30

# Check deployment status
railway status

echo ""

# =============================================================================
# Step 8: Get Webhook URL
# =============================================================================

log_info "Step 8: Getting webhook URL..."

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
    echo "📋 Next Steps:"
    echo ""
    echo "1. Configure Twilio Webhook:"
    echo "   - Go to: https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox"
    echo "   - Set 'When a message comes in' to:"
    echo "     $WEBHOOK_URL"
    echo "   - Method: POST"
    echo "   - Click Save"
    echo ""
    echo "2. Run validation:"
    echo "   ./scripts/validate-deployment.sh $ENV_NAME"
    echo ""
    echo "3. Test with WhatsApp:"
    echo "   ./scripts/test-whatsapp-e2e.sh $ENV_NAME"
    echo ""
    echo "4. Monitor logs:"
    echo "   railway logs --environment $ENV_NAME --follow"
    echo ""

    # Copy to clipboard if possible
    if command -v pbcopy &> /dev/null; then
        echo "$WEBHOOK_URL" | pbcopy
        log_success "Webhook URL copied to clipboard"
    elif command -v xclip &> /dev/null; then
        echo "$WEBHOOK_URL" | xclip -selection clipboard
        log_success "Webhook URL copied to clipboard"
    fi

else
    log_error "Could not retrieve domain"
    log_info "Get it manually with: railway domain"
fi

echo ""
log_success "🎉 Deployment complete!"
echo ""
