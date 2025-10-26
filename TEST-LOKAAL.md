# Lokaal Testen met Twilio Sandbox

## OPTIE A: Ngrok (Aanbevolen voor lokaal testen)

### Stap 1: Start je FastAPI app
```bash
cd /Users/benomarlaamiri/Claude\ code\ project/seldenrijk-auto-whatsapp
uvicorn webhook_twilio_sandbox:app --reload --port 8000
```

### Stap 2: Start ngrok in nieuw terminal window
```bash
ngrok http 8000
```

Je krijgt een URL zoals: `https://abc123.ngrok.io`

### Stap 3: Configureer Twilio Webhook
Ga naar: https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox

Bij "When a message comes in" vul in:
```
https://abc123.ngrok.io/webhook/twilio
```

Klik **Save**

### Stap 4: Test!
1. Stuur WhatsApp bericht naar +1 415 523 8886
2. Type: "hallo"
3. Je krijgt direct response van chatbot! 🎉

---

## OPTIE B: Direct naar Railway (Sneller, geen ngrok nodig)

### Stap 1: Push code naar Railway
```bash
git add webhook_twilio_sandbox.py
git commit -m "Add Twilio Sandbox webhook"
git push
```

Railway auto-deployt binnen 2 minuten.

### Stap 2: Configureer Twilio Webhook
Je Railway URL is zoiets als:
```
https://seldenrijk-auto-whatsapp.up.railway.app/webhook/twilio
```

Vul deze in bij Twilio dashboard (zie boven).

### Stap 3: Test!
Stuur WhatsApp bericht → instant response! ✅

---

## TEST COMMANDO'S:

Probeer deze berichten in WhatsApp:

1. **"hallo"** → Welkomstbericht
2. **"auto"** → Aanbod overzicht
3. **"1"** → Volkswagen Golf details
4. **"proefrit"** → Proefrit plannen
5. **"prijs"** → Financiering info

---

## CURL TEST (vanuit terminal):

Test je endpoint direct:
```bash
curl -X POST https://[JOUW-URL]/webhook/twilio \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "Body=hallo" \
  -d "From=whatsapp:+31612345678" \
  -d "To=whatsapp:+14155238886" \
  -d "MessageSid=TEST123"
```

Je zou JSON response moeten zien met `"status": "success"`

---

## TROUBLESHOOTING:

❌ **"Forbidden" error**
→ Check je Twilio credentials in code

❌ **"No response" in WhatsApp**
→ Check of webhook URL correct is in Twilio dashboard

❌ **"Connection timeout"**
→ Is je FastAPI app running? Check logs

✅ **Logs checken:**
```bash
# Railway logs
railway logs

# Lokaal
Check terminal waar uvicorn draait
```
