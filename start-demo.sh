#!/bin/bash
# ============================================
# WhatsApp Recruitment Platform - Demo Startup
# Quick start script voor local Docker demo
# ============================================

set -e  # Exit on error

# Colors voor output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Header
clear
print_header "WhatsApp Recruitment Platform - Demo Setup"
echo ""

# Step 1: Check Docker
print_info "Stap 1/6: Checking Docker..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is niet geïnstalleerd!"
    echo "Download: https://docs.docker.com/desktop/install/mac-install/"
    exit 1
fi

if ! docker info &> /dev/null; then
    print_error "Docker Desktop is niet gestart!"
    echo "Start Docker Desktop en probeer opnieuw."
    exit 1
fi

print_success "Docker is geïnstalleerd en draait"
echo ""

# Step 2: Check .env file
print_info "Stap 2/6: Checking environment variables..."
if [ ! -f .env ]; then
    if [ -f .env.local ]; then
        print_warning ".env file niet gevonden, kopiëren van .env.local..."
        cp .env.local .env
        print_success ".env file aangemaakt"
        print_warning "⚠️  BELANGRIJES: Vul je API keys in .env file in!"
        echo "   Edit met: nano .env"
        echo ""
        read -p "Druk op Enter als je .env hebt geconfigureerd..."
    else
        print_error ".env file niet gevonden!"
        echo "Kopieer .env.example naar .env en vul API keys in:"
        echo "  cp .env.example .env"
        echo "  nano .env"
        exit 1
    fi
fi

# Check critical env vars
required_vars=("ANTHROPIC_API_KEY" "OPENAI_API_KEY" "SUPABASE_URL" "SUPABASE_KEY" "CHATWOOT_SECRET_KEY_BASE" "CHATWOOT_POSTGRES_PASSWORD")
missing_vars=()

source .env
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ] || [[ "${!var}" == *"xxx"* ]]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_error "Missing of incomplete environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Vul deze in .env file in en run opnieuw:"
    echo "  nano .env"
    exit 1
fi

print_success "Alle vereiste environment variables zijn ingesteld"
echo ""

# Step 3: Stop oude containers
print_info "Stap 3/6: Stopping oude containers..."
docker-compose -f docker-compose.full.yml down -v &> /dev/null || true
print_success "Oude containers gestopt"
echo ""

# Step 4: Build containers
print_info "Stap 4/6: Building Docker containers..."
echo "Dit kan 2-3 minuten duren bij eerste keer..."
if docker-compose -f docker-compose.full.yml build --no-cache > /tmp/docker-build.log 2>&1; then
    print_success "Containers gebouwd"
else
    print_error "Build failed! Check logs:"
    echo ""
    cat /tmp/docker-build.log
    exit 1
fi
echo ""

# Step 5: Start services
print_info "Stap 5/6: Starting services..."
if docker-compose -f docker-compose.full.yml up -d > /tmp/docker-up.log 2>&1; then
    print_success "Services gestart"
else
    print_error "Failed to start services! Check logs:"
    echo ""
    cat /tmp/docker-up.log
    exit 1
fi
echo ""

# Wait for services to be healthy
print_info "Waiting for services to be healthy..."
echo "Checking health status..."

max_attempts=30
attempt=0
all_healthy=false

while [ $attempt -lt $max_attempts ]; do
    attempt=$((attempt + 1))

    # Check API health
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        all_healthy=true
        break
    fi

    echo -n "."
    sleep 2
done

echo ""

if [ "$all_healthy" = true ]; then
    print_success "Alle services zijn healthy!"
else
    print_warning "Services nog niet klaar na 60 seconden"
    print_info "Services kunnen nog opstarten, check met: docker-compose ps"
fi
echo ""

# Step 6: Verify setup
print_info "Stap 6/6: Verifying setup..."

# Check containers
running_containers=$(docker-compose -f docker-compose.full.yml ps --services --filter "status=running" | wc -l)
total_containers=$(docker-compose -f docker-compose.full.yml ps --services | wc -l)

if [ "$running_containers" -eq "$total_containers" ]; then
    print_success "Alle $running_containers containers draaien"
else
    print_warning "$running_containers van $total_containers containers draaien"
fi

# Check Chatwoot
if curl -sf http://localhost:3001/api > /dev/null 2>&1; then
    print_success "Chatwoot dashboard bereikbaar"
else
    print_warning "Chatwoot nog niet bereikbaar (kan 30-60 seconden duren)"
fi

# Check API
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    print_success "API health check passed"
else
    print_warning "API nog niet bereikbaar"
fi

# Check Redis
if docker-compose -f docker-compose.full.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    print_success "Redis is bereikbaar"
else
    print_warning "Redis nog niet bereikbaar"
fi

echo ""

# Final summary
print_header "🚀 Demo Setup Complete!"
echo ""
print_success "Services draaien op:"
echo "  • Chatwoot:  http://localhost:3001 (CRM Dashboard)"
echo "  • API:       http://localhost:8000"
echo "  • Health:    http://localhost:8000/health"
echo "  • Metrics:   http://localhost:8000/metrics"
echo "  • Dashboard: http://localhost:3002 (Reflex Metrics)"
echo ""

print_info "Handige commando's:"
echo "  • Logs bekijken:        docker-compose -f docker-compose.full.yml logs -f"
echo "  • Logs van 1 service:   docker-compose -f docker-compose.full.yml logs -f api"
echo "  • Services herstarten:  docker-compose -f docker-compose.full.yml restart"
echo "  • Services stoppen:     docker-compose -f docker-compose.full.yml down"
echo ""

# Check ngrok
if ! command -v ngrok &> /dev/null; then
    print_warning "ngrok niet geïnstalleerd (vereist voor WhatsApp webhooks)"
    echo "   Install met: brew install ngrok"
    echo "   Start met:   ngrok http 8000"
else
    print_info "ngrok geïnstalleerd - start met: ngrok http 8000"
fi
echo ""

# Demo scenarios
print_info "📚 Demo Scenarios:"
echo "   Zie DOCKER-LOCAL-DEMO-GUIDE.md voor complete demo scripts"
echo "   Belangrijkste scenarios:"
echo "   1. Job Search Demo"
echo "   2. Complaint Escalation"
echo "   3. Multi-Turn Conversation"
echo ""

# Chatwoot setup reminder
if grep -q "CHATWOOT_API_TOKEN=$" .env 2>/dev/null || grep -q "CHATWOOT_API_TOKEN=  #" .env 2>/dev/null; then
    print_warning "Chatwoot nog niet volledig geconfigureerd!"
    echo ""
    echo "   VOLGENDE STAPPEN:"
    echo "   1. Open Chatwoot: http://localhost:3001"
    echo "   2. Create admin account"
    echo "   3. Generate API token (Settings → Integrations → API)"
    echo "   4. Update CHATWOOT_API_TOKEN in .env"
    echo "   5. Restart services: docker-compose -f docker-compose.full.yml restart api celery-worker"
    echo ""
fi

# WhatsApp setup reminder
if grep -q "DIALOG360_API_KEY=xxx" .env 2>/dev/null || grep -q "DIALOG360_API_KEY=$" .env 2>/dev/null; then
    print_warning "360Dialog API key nog niet ingesteld"
    echo "   Voor echte WhatsApp integratie:"
    echo "   1. Sign up op https://hub.360dialog.com/"
    echo "   2. Vul DIALOG360_API_KEY in .env in"
    echo "   3. Configureer webhook (zie guide)"
fi
echo ""

print_success "🎉 Setup compleet! Begin met demo!"
print_info "Check logs met: docker-compose -f docker-compose.full.yml logs -f"
echo ""
