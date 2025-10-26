#!/bin/bash

# Auto-configure Twilio Sandbox Webhook
# Usage: ./configure-twilio.sh <railway-url>

set -e

RAILWAY_URL="$1"
TWILIO_ACCOUNT_SID="${TWILIO_ACCOUNT_SID:-$(grep TWILIO_ACCOUNT_SID RAILWAY-VARIABLES.txt | cut -d'=' -f2)}"
TWILIO_AUTH_TOKEN="${TWILIO_AUTH_TOKEN:-$(grep TWILIO_AUTH_TOKEN RAILWAY-VARIABLES.txt | cut -d'=' -f2)}"

if [ -z "$RAILWAY_URL" ]; then
    echo "❌ Error: Please provide Railway URL"
    echo "Usage: ./configure-twilio.sh https://your-app.up.railway.app"
    exit 1
fi

echo "🔧 Configuring Twilio Sandbox Webhook..."
echo "📍 Railway URL: $RAILWAY_URL"
echo "🔑 Account SID: $TWILIO_ACCOUNT_SID"

# Configure webhook
WEBHOOK_URL="${RAILWAY_URL}/webhook/twilio"

echo "📡 Setting webhook to: $WEBHOOK_URL"

# Use Twilio API to configure sandbox
curl -X POST "https://api.twilio.com/2010-04-01/Accounts/${TWILIO_ACCOUNT_SID}/IncomingPhoneNumbers.json" \
  -u "${TWILIO_ACCOUNT_SID}:${TWILIO_AUTH_TOKEN}" \
  --data-urlencode "SmsUrl=${WEBHOOK_URL}" \
  --data-urlencode "SmsMethod=POST" \
  || echo "⚠️  Note: May need to configure via Twilio Console instead"

echo ""
echo "✅ Configuration attempted!"
echo ""
echo "📋 Manual verification steps:"
echo "1. Go to: https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox"
echo "2. Verify webhook URL is: $WEBHOOK_URL"
echo "3. Method should be: POST"
echo ""
echo "🧪 Test with WhatsApp:"
echo "1. Send message to: +1 415 523 8886"
echo "2. First send: join <sandbox-code>"
echo "3. Then send: hallo"
echo ""
echo "✅ You should receive a welcome message!"
