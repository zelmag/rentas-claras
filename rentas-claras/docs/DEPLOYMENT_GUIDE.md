# 🚀 Deployment Guide: RentasClaras on Fly.io

This guide walks you through deploying RentasClaras to Fly.io and configuring Meta webhooks for real-time message status tracking (delivered, read, replied).

---

## Prerequisites

1. **Fly.io Account**: Sign up free at https://fly.io
2. **Fly CLI**: Install with `brew install flyctl` (Mac) or see https://fly.io/docs/hands-on/install-flyctl/
3. **WhatsApp Business API**: Already configured in your Meta Developer Portal

---

## Step 1: Install Fly CLI & Login

```bash
# Install Fly CLI (Mac)
brew install flyctl

# Login to Fly.io
fly auth login
```

---

## Step 2: Deploy to Fly.io

```bash
# Navigate to your project
cd /Users/zelma/Desktop/ZelmaHelps_Agent/rentas-claras

# First-time deployment (creates the app)
fly launch

# When prompted:
# - App name: rentas-claras (or choose your own)
# - Region: dfw (Dallas) - good for Mexico
# - PostgreSQL: No (we use SQLite)
# - Redis: No
# - Deploy now: No (we need to set secrets first)
```

---

## Step 3: Set Secret Environment Variables

```bash
# Required secrets
fly secrets set SECRET_KEY="your-flask-secret-key-here"
fly secrets set RENTASCLARAS_PIN="your-4-digit-pin"
fly secrets set WHATSAPP_ACCESS_TOKEN="your-whatsapp-access-token"
fly secrets set WHATSAPP_PHONE_NUMBER_ID="your-phone-number-id"
fly secrets set WHATSAPP_WEBHOOK_VERIFY_TOKEN="create-a-random-string-for-verification"

# Optional (for webhook signature verification)
fly secrets set WHATSAPP_APP_SECRET="your-app-secret-from-meta"
```

### Get Your Values:
- **SECRET_KEY**: Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
- **RENTASCLARAS_PIN**: Same PIN you use locally
- **WHATSAPP_ACCESS_TOKEN**: From Meta Developer Portal → WhatsApp → API Setup
- **WHATSAPP_PHONE_NUMBER_ID**: From Meta Developer Portal → WhatsApp → API Setup
- **WHATSAPP_WEBHOOK_VERIFY_TOKEN**: Create any random string (you'll use this in Meta)
- **WHATSAPP_APP_SECRET**: From Meta Developer Portal → Settings → Basic

---

## Step 4: Deploy!

```bash
# Deploy the app
fly deploy

# Check status
fly status

# View logs
fly logs
```

Your app will be live at: **https://rentas-claras.fly.dev** (or your chosen name)

---

## Step 5: Configure Meta Webhook

Now the important part - connecting Meta to your app so you receive delivery receipts.

### 5.1 Go to Meta Developer Portal
1. Visit https://developers.facebook.com/apps/
2. Select your WhatsApp app
3. Click **Webhooks** in the left sidebar

### 5.2 Configure Webhook
1. Click **Edit** next to the WhatsApp webhook
2. Enter these values:
   - **Callback URL**: `https://rentas-claras.fly.dev/webhook/whatsapp`
   - **Verify Token**: The same `WHATSAPP_WEBHOOK_VERIFY_TOKEN` you set in Fly.io secrets

3. Click **Verify and Save**

### 5.3 Subscribe to Webhook Fields
After verification succeeds, subscribe to these fields:
- ✅ `messages` - Incoming messages from tenants
- ✅ `message_status` - Delivery receipts (sent, delivered, read)

Click **Done** to save.

---

## Step 6: Test It!

1. Open your deployed app: https://rentas-claras.fly.dev
2. Log in with your PIN
3. Go to **Recordatorios** and send a test message (use Hello World template)
4. Wait a few seconds
5. Go back to **Resumen** (dashboard) - you should see the message status widget update!

### What to Expect:
- **Enviados**: Updates immediately when you send
- **Entregados**: Updates within seconds when the message reaches the phone
- **Leídos**: Updates when the tenant opens WhatsApp and reads the message
- **Respuestas**: Updates when the tenant replies

---

## Troubleshooting

### Webhook Not Receiving Events?

1. **Check webhook is verified**:
   ```bash
   # View your app's logs
   fly logs
   ```
   Look for "Webhook verified successfully!" message.

2. **Check Meta webhook status**:
   - Go to Meta Developer Portal → Webhooks
   - Click "Test" next to a subscribed field
   - Check fly logs for incoming requests

3. **Check webhook URL is correct**:
   - Must be HTTPS
   - Must end with `/webhook/whatsapp`

### Messages Not Sending?

1. **Check WhatsApp credentials**:
   ```bash
   fly secrets list  # Should show all secrets are set
   ```

2. **Check access token hasn't expired**:
   - Meta access tokens expire after ~60 days
   - Generate a new one in Meta Developer Portal

---

## Updating Your App

After making code changes locally:

```bash
# Deploy updates
fly deploy

# View deployment status
fly status
```

---

## Useful Fly Commands

```bash
# View logs
fly logs

# SSH into the container
fly ssh console

# Check app status
fly status

# Scale (if needed)
fly scale count 1

# View secrets
fly secrets list

# Update a secret
fly secrets set KEY=new_value
```

---

## Cost

Fly.io free tier includes:
- 3 shared-CPU VMs
- 160 GB outbound transfer/month
- Free SSL certificates

RentasClaras runs on 1 small VM (~$3-5/month if you exceed free tier).

---

## Next Steps

1. ✅ Deploy to Fly.io
2. ✅ Configure Meta webhook
3. ✅ Test message status tracking
4. 📱 Get your custom templates approved by Meta
5. 🎉 Use the full reminder system!

---

**Need Help?**

- Fly.io Docs: https://fly.io/docs/
- Meta WhatsApp Docs: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks
