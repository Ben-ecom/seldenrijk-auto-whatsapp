#!/bin/bash
# =============================================================================
# Doppler + Railway Deployment Automation
# Enterprise-grade secret management for Seldenrijk Auto WhatsApp System
# =============================================================================
# Based on research: ENTERPRISE-SAAS-DEPLOYMENT-GUIDE.md
# Total execution time: ~15 minutes
# =============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="seldenrijk-auto"
STAGING_CONFIG="staging"
PRODUCTION_CONFIG="production"

# =============================================================================
# Helper Functions
# =============================================================================

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
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed"
        return 1
    fi
    log_success "$1 is installed"
    return 0
}

# =============================================================================
# Step 1: Verify Prerequisites (2 minutes)
# =============================================================================

step1_verify_prerequisites() {
    log_info "Step 1: Verifying prerequisites..."

    local all_good=true

    # Check Doppler CLI
    if ! check_command "doppler"; then
        log_warning "Installing Doppler CLI..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install dopplerhq/cli/doppler
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            (curl -Ls --tlsv1.2 --proto "=https" --retry 3 https://cli.doppler.com/install.sh || wget -t 3 -qO- https://cli.doppler.com/install.sh) | sudo sh
        else
            log_error "Unsupported OS. Please install Doppler manually from: https://docs.doppler.com/docs/install-cli"
            all_good=false
        fi
    fi

    # Check Railway CLI
    if ! check_command "railway"; then
        log_warning "Installing Railway CLI..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install railway
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            curl -fsSL https://railway.app/install.sh | sh
        else
            log_error "Unsupported OS. Please install Railway manually from: https://railway.app/install"
            all_good=false
        fi
    fi

    # Check jq (for JSON parsing)
    if ! check_command "jq"; then
        log_warning "Installing jq..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            brew install jq
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo apt-get install -y jq
        fi
    fi

    if $all_good; then
        log_success "✅ All prerequisites installed"
        return 0
    else
        log_error "❌ Some prerequisites are missing. Please install them manually."
        return 1
    fi
}

# =============================================================================
# Step 2: Doppler Authentication (1 minute)
# =============================================================================

step2_doppler_auth() {
    log_info "Step 2: Authenticating with Doppler..."

    # Check if already logged in
    if doppler me &> /dev/null; then
        log_success "Already authenticated with Doppler"
        doppler me
        return 0
    fi

    log_warning "Not authenticated. Opening browser for login..."
    doppler login

    if doppler me &> /dev/null; then
        log_success "✅ Doppler authentication successful"
        return 0
    else
        log_error "❌ Doppler authentication failed"
        return 1
    fi
}

# =============================================================================
# Step 3: Create Doppler Project & Configs (2 minutes)
# =============================================================================

step3_create_doppler_project() {
    log_info "Step 3: Creating Doppler project and configurations..."

    # Create project if it doesn't exist
    if doppler projects get "$PROJECT_NAME" &> /dev/null; then
        log_success "Project '$PROJECT_NAME' already exists"
    else
        log_info "Creating project '$PROJECT_NAME'..."
        doppler projects create "$PROJECT_NAME" --description "Seldenrijk Auto WhatsApp System"
        log_success "✅ Project created"
    fi

    # Create staging config if it doesn't exist
    if doppler configs get "$STAGING_CONFIG" --project "$PROJECT_NAME" &> /dev/null; then
        log_success "Staging config already exists"
    else
        log_info "Creating staging config..."
        doppler configs create "$STAGING_CONFIG" --project "$PROJECT_NAME"
        log_success "✅ Staging config created"
    fi

    # Create production config if it doesn't exist
    if doppler configs get "$PRODUCTION_CONFIG" --project "$PROJECT_NAME" &> /dev/null; then
        log_success "Production config already exists"
    else
        log_info "Creating production config..."
        doppler configs create "$PRODUCTION_CONFIG" --project "$PROJECT_NAME"
        log_success "✅ Production config created"
    fi

    log_success "✅ Doppler project structure ready"
}

# =============================================================================
# Step 4: Add Twilio Secrets (Interactive - User Provides Credentials)
# =============================================================================

step4_add_twilio_secrets() {
    local environment=$1  # "staging" or "production"

    log_info "Step 4: Adding Twilio secrets to $environment..."

    # Setup Doppler context for this environment
    doppler setup --project "$PROJECT_NAME" --config "$environment" --no-interactive

    echo ""
    log_warning "You need to provide your Twilio credentials for $environment:"
    echo ""

    # Prompt for credentials
    read -p "Twilio Account SID (starts with AC...): " TWILIO_ACCOUNT_SID
    read -sp "Twilio Auth Token: " TWILIO_AUTH_TOKEN
    echo ""
    read -p "Twilio WhatsApp Number (format: whatsapp:+31850000000): " TWILIO_WHATSAPP_NUMBER

    # Validate inputs
    if [[ ! $TWILIO_ACCOUNT_SID =~ ^AC[a-f0-9]{32}$ ]]; then
        log_error "Invalid Account SID format"
        return 1
    fi

    if [[ -z "$TWILIO_AUTH_TOKEN" ]]; then
        log_error "Auth Token cannot be empty"
        return 1
    fi

    if [[ ! $TWILIO_WHATSAPP_NUMBER =~ ^whatsapp:\+ ]]; then
        log_error "Invalid WhatsApp number format (should start with 'whatsapp:+')"
        return 1
    fi

    # Add secrets to Doppler
    log_info "Adding secrets to Doppler..."

    echo "$TWILIO_ACCOUNT_SID" | doppler secrets set TWILIO_ACCOUNT_SID --config "$environment" --project "$PROJECT_NAME"
    echo "$TWILIO_AUTH_TOKEN" | doppler secrets set TWILIO_AUTH_TOKEN --config "$environment" --project "$PROJECT_NAME"
    echo "$TWILIO_WHATSAPP_NUMBER" | doppler secrets set TWILIO_WHATSAPP_NUMBER --config "$environment" --project "$PROJECT_NAME"

    # Add other required secrets
    log_info "Adding other required secrets..."

    # Read from current .env.example to get other required vars
    if [[ -f ".env.example" ]]; then
        while IFS='=' read -r key _; do
            # Skip comments and empty lines
            [[ "$key" =~ ^#.*$ ]] && continue
            [[ -z "$key" ]] && continue

            # Skip Twilio vars (already added)
            [[ "$key" == "TWILIO_ACCOUNT_SID" ]] && continue
            [[ "$key" == "TWILIO_AUTH_TOKEN" ]] && continue
            [[ "$key" == "TWILIO_WHATSAPP_NUMBER" ]] && continue

            # Check if secret already exists
            if doppler secrets get "$key" --config "$environment" --project "$PROJECT_NAME" &> /dev/null; then
                log_success "Secret $key already exists"
            else
                # Prompt for value
                read -p "Enter value for $key (or press Enter to skip): " value
                if [[ -n "$value" ]]; then
                    echo "$value" | doppler secrets set "$key" --config "$environment" --project "$PROJECT_NAME"
                    log_success "Added $key"
                fi
            fi
        done < .env.example
    fi

    log_success "✅ Secrets added to Doppler $environment"

    # Display secrets (values hidden)
    log_info "Current secrets in $environment:"
    doppler secrets --config "$environment" --project "$PROJECT_NAME"
}

# =============================================================================
# Step 5: Railway Authentication (1 minute)
# =============================================================================

step5_railway_auth() {
    log_info "Step 5: Authenticating with Railway..."

    # Check if already logged in
    if railway whoami &> /dev/null; then
        log_success "Already authenticated with Railway"
        railway whoami
        return 0
    fi

    log_warning "Not authenticated. Opening browser for login..."
    railway login

    if railway whoami &> /dev/null; then
        log_success "✅ Railway authentication successful"
        return 0
    else
        log_error "❌ Railway authentication failed"
        return 1
    fi
}

# =============================================================================
# Step 6: Link Railway Project (1 minute)
# =============================================================================

step6_railway_link() {
    log_info "Step 6: Linking Railway project..."

    # Check if already linked
    if railway status &> /dev/null; then
        log_success "Already linked to Railway project"
        railway status
        return 0
    fi

    log_info "Linking to Railway project..."
    railway link

    if railway status &> /dev/null; then
        log_success "✅ Railway project linked"
        return 0
    else
        log_error "❌ Failed to link Railway project"
        return 1
    fi
}

# =============================================================================
# Step 7: Doppler-Railway Integration (5 minutes)
# =============================================================================

step7_doppler_railway_integration() {
    log_info "Step 7: Setting up Doppler-Railway integration..."

    log_warning "You need to complete this step in the Railway dashboard:"
    echo ""
    echo "1. Open Railway dashboard: https://railway.app/dashboard"
    echo "2. Select your project: seldenrijk-auto-whatsapp"
    echo "3. Go to: Settings → Integrations"
    echo "4. Click: Add Integration → Doppler"
    echo "5. Authorize Railway in Doppler"
    echo "6. Select:"
    echo "   - Project: $PROJECT_NAME"
    echo "   - Staging Config: $STAGING_CONFIG"
    echo "   - Production Config: $PRODUCTION_CONFIG"
    echo ""

    read -p "Press Enter when you've completed the integration..."

    log_success "✅ Doppler-Railway integration configured"
    log_info "Secrets will now auto-sync from Doppler to Railway"
}

# =============================================================================
# Step 8: Deploy to Staging (2 minutes)
# =============================================================================

step8_deploy_staging() {
    log_info "Step 8: Deploying to Railway staging..."

    # Switch to staging environment
    railway environment staging

    # Deploy
    log_info "Starting deployment..."
    railway up

    # Wait for deployment
    log_info "Waiting for deployment to complete..."
    sleep 10

    # Get deployment status
    railway status

    log_success "✅ Deployed to staging"

    # Get webhook URL
    log_info "Getting webhook URL..."
    WEBHOOK_URL=$(railway domain)

    if [[ -n "$WEBHOOK_URL" ]]; then
        log_success "Webhook URL: https://$WEBHOOK_URL/api/webhooks/twilio"
        echo ""
        log_warning "Configure this URL in Twilio Console:"
        echo "1. Go to: https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox"
        echo "2. Set 'When a message comes in' to: https://$WEBHOOK_URL/api/webhooks/twilio"
        echo "3. Method: POST"
        echo ""
    else
        log_error "Could not retrieve webhook URL"
        log_info "Get it manually with: railway domain"
    fi
}

# =============================================================================
# Step 9: Validation & Testing (5 minutes)
# =============================================================================

step9_validate_deployment() {
    log_info "Step 9: Validating deployment..."

    # Get Railway domain
    DOMAIN=$(railway domain)

    if [[ -z "$DOMAIN" ]]; then
        log_error "Could not get Railway domain"
        return 1
    fi

    BASE_URL="https://$DOMAIN"

    # Test health endpoint
    log_info "Testing health endpoint..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")

    if [[ "$HTTP_CODE" == "200" ]]; then
        log_success "✅ Health check passed (HTTP $HTTP_CODE)"
    else
        log_error "❌ Health check failed (HTTP $HTTP_CODE)"
        return 1
    fi

    # Test Twilio webhook endpoint
    log_info "Testing Twilio webhook endpoint..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/webhooks/twilio")

    if [[ "$HTTP_CODE" == "405" || "$HTTP_CODE" == "401" ]]; then
        log_success "✅ Twilio webhook endpoint exists (HTTP $HTTP_CODE - expected for GET request)"
    else
        log_warning "⚠️  Twilio webhook returned HTTP $HTTP_CODE"
    fi

    # Check environment variables
    log_info "Checking environment variables in Railway..."
    railway variables

    log_success "✅ Deployment validation complete"

    echo ""
    log_warning "NEXT STEPS:"
    echo "1. Send a test WhatsApp message to your Twilio sandbox number"
    echo "2. Check Railway logs: railway logs"
    echo "3. Verify message is processed correctly"
    echo "4. If successful, proceed with production deployment"
    echo ""
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo ""
    echo "============================================================================="
    echo "  Doppler + Railway Deployment for Seldenrijk Auto WhatsApp System"
    echo "============================================================================="
    echo ""

    # Run all steps
    step1_verify_prerequisites || exit 1
    step2_doppler_auth || exit 1
    step3_create_doppler_project || exit 1

    # Add secrets for staging
    step4_add_twilio_secrets "staging" || exit 1

    # Railway setup
    step5_railway_auth || exit 1
    step6_railway_link || exit 1
    step7_doppler_railway_integration || exit 1

    # Deploy and validate
    step8_deploy_staging || exit 1
    step9_validate_deployment || exit 1

    echo ""
    log_success "🎉 Deployment complete!"
    echo ""
    log_info "To deploy to production, run:"
    echo "  ./scripts/doppler-setup.sh production"
    echo ""
}

# Check if production mode
if [[ "${1:-}" == "production" ]]; then
    log_warning "PRODUCTION MODE - Adding production secrets"
    step4_add_twilio_secrets "production"
    exit 0
fi

# Run main
main
