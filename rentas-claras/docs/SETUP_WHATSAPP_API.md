# WhatsApp Cloud API Setup Guide for RentasClaras

## Overview

This guide walks you through setting up Meta's WhatsApp Cloud API to send automated rent reminders.

**Cost:** FREE for first 1,000 messages/month (you'll use ~160)

**Time:** ~30 minutes of setup + 1-3 days for business verification

---

## 🚦 CURRENT STATUS (Updated: Dec 28, 2024)

### Where We Left Off:
- ✅ Code integration complete (`whatsapp_client.py`, API endpoints, UI button)
- ✅ `.env.example` created with all required variables
- ✅ `requirements.txt` updated with `requests` and `python-dotenv`
- ⏳ **BLOCKED:** Need to create Meta Developer Account with a NON-work Facebook account

### Next Steps Tomorrow:
1. **Your dad creates the developer account** (recommended) — OR —
2. **You use a personal Facebook account** in incognito mode (no Meta employee detection)

### Credentials Needed (to fill in `.env`):
```
WHATSAPP_ACCESS_TOKEN=EAAxxxx...     ← Get from Step 4
WHATSAPP_PHONE_NUMBER_ID=123456...   ← Get from Step 4
```

---

## ⚠️ IMPORTANT: Meta Employee Note

If you're a Meta employee, the developer portal will detect this and block personal apps.

**Solution:** Use a **completely separate Facebook account** that has no connection to your Meta work identity:

1. **Best option:** Have your dad (the business owner) create the developer account using his Facebook
2. **Alternative:** Use a personal Facebook account in a private/incognito browser window
3. **Make sure:** You're logged out of ALL Meta/Facebook/Workplace accounts before starting

---

## Step 1: Create Meta Developer Account

### If Your Dad is Doing This:

1. Go to **https://developers.facebook.com**
2. Log in with **his** Facebook account (create one if needed)
3. Click "Get Started"
4. Accept developer terms
5. Verify phone/email if prompted

### If You're Doing This (Non-Work Account):

1. **Open incognito/private browser window**
2. Go to **https://developers.facebook.com**
3. Log in with a **personal** Facebook account (NOT connected to Meta work)
4. Click "Get Started"
5. Accept developer terms

---

## Step 2: Create a Business App

1. Go to **https://developers.facebook.com/apps**
2. Click **"Create App"**
3. Select **"Other"** → **"Business"**
4. Enter app name: `RentasClaras` (or any name you want)
5. Enter contact email
6. Click **"Create App"**

---

## Step 3: Add WhatsApp Product

1. In your app dashboard, find **"Add products to your app"**
2. Find **"WhatsApp"** and click **"Set Up"**
3. You'll be taken to WhatsApp setup page

---

## Step 4: Get Test Credentials (for development)

Meta gives you **temporary test credentials** immediately:

1. On the WhatsApp setup page, you'll see:
   - **Phone number ID**: `1234567890` (example)
   - **Temporary access token**: A long string starting with `EAA...`

2. **Copy both** and save them somewhere safe.

> ⚠️ The temporary token expires in 24 hours. We'll get a permanent one later.

---

## Step 5: Add Test Phone Numbers

Before verification, you can only send to **verified test numbers**:

1. In WhatsApp setup, go to **"API Setup"**
2. Under **"Send and receive messages"**, find **"To" field**
3. Click **"Manage phone number list"**
4. Add your phone number (for testing)
5. You'll receive a verification code via WhatsApp
6. Enter the code to verify

Now you can send test messages to this number.

---

## Step 6: Create Message Templates

WhatsApp requires **approved templates** for outbound messages:

1. Go to **WhatsApp Manager** → **Message Templates** (or find it in the left sidebar)
2. Click **"Create Template"**

### Template 1: Rent Reminder (Day 1)

| Field | Value |
|-------|-------|
| **Name** | `rent_reminder` |
| **Category** | `UTILITY` |
| **Language** | `Spanish (Mexico)` - es_MX |

**Body:**
```
Buenos días {{1}}. Espero esté bien. Para recordarle por favor del pago de la renta de {{2}}. Total: ${{3}} MXN. Gracias.
```

Variables:
- `{{1}}` = Tenant name (e.g., "María")
- `{{2}}` = Month (e.g., "enero")
- `{{3}}` = Amount (e.g., "3,200")

3. Click **"Submit"** → Wait for approval (usually 24-48 hours)

### Template 2: Late Reminder (Day 3+)

| Field | Value |
|-------|-------|
| **Name** | `rent_reminder_late` |
| **Category** | `UTILITY` |
| **Language** | `Spanish (Mexico)` - es_MX |

**Body:**
```
Buenas tardes {{1}}. Le recordamos que el pago de renta de {{2}} por ${{3}} MXN sigue pendiente. Por favor regularice su situación. Gracias.
```

4. Submit and wait for approval.

---

## Step 7: Business Verification (Required for Production)

To message anyone (not just test numbers), you need to verify your business:

1. Go to **https://business.facebook.com/settings**
2. Click **"Business Info"** in left sidebar
3. Click **"Start Verification"**

### What you'll need:
- **Business name**: "Administración de Rentas Garza" (or similar)
- **Business address**: Your dad's address
- **Phone number**: Business phone
- **Document**: ONE of:
  - Utility bill with business name/address
  - Bank statement
  - Business registration (if you have one)
  - Tax document

### Verification takes 1-3 business days.

---

## Step 8: Get Permanent Access Token

After verification, get a token that doesn't expire:

1. Go to **https://developers.facebook.com/apps** → Your app
2. Go to **Settings** → **Basic**
3. Note your **App ID** and **App Secret**

4. Go to **https://developers.facebook.com/tools/explorer/**
5. Select your app
6. Click **"Generate Access Token"**
7. Add permission: `whatsapp_business_messaging`
8. Copy the token

For a **permanent token**, you'll need to:
1. Go to **Business Settings** → **System Users**
2. Create a System User with Admin role
3. Generate a token for that user with `whatsapp_business_messaging` permission

---

## Step 9: Register Your Phone Number (Optional)

You can use Meta's test number OR register your own:

1. Go to WhatsApp Manager → **Phone Numbers**
2. Click **"Add Phone Number"**
3. Enter the phone number (must not be registered on regular WhatsApp)
4. Verify via SMS or voice call
5. You'll get a new **Phone Number ID** for this number

---

## Step 10: Configure RentasClaras

1. Copy your credentials to `.env`:

```bash
# WhatsApp Cloud API Credentials
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=1234567890
WHATSAPP_BUSINESS_ACCOUNT_ID=9876543210
```

2. Test the integration:

```bash
cd rentas-claras
python -c "from src.whatsapp_client import send_test_message; send_test_message()"
```

---

## Quick Reference: API Endpoints

| Action | Endpoint |
|--------|----------|
| Send message | `POST /v18.0/{phone_number_id}/messages` |
| Get templates | `GET /v18.0/{business_id}/message_templates` |
| Upload media | `POST /v18.0/{phone_number_id}/media` |

Base URL: `https://graph.facebook.com`

---

## Troubleshooting

### "Message failed to send"
- Check if recipient has WhatsApp installed
- Verify phone number format: `521234567890` (country code, no +)

### "Template not found"
- Wait for template approval (check status in WhatsApp Manager)
- Check template name matches exactly (case-sensitive)

### "Invalid token"
- Token may have expired → generate a new one
- Check token has `whatsapp_business_messaging` permission

### "User not in allowed list"
- Business not verified yet → can only send to test numbers
- Add recipient to test numbers list

---

## Cost Summary

| Type | Free Tier | After Free |
|------|-----------|------------|
| Service conversations | 1,000/month | ~$0.005/msg |
| Marketing conversations | 1,000/month | ~$0.01/msg |

Your usage (~160 messages/month) = **$0**

---

## Next Steps

After setup is complete:

1. ✅ Templates approved
2. ✅ Business verified
3. ✅ Credentials in `.env`
4. Run the app: `python app.py`
5. Go to `http://localhost:5000`
6. Click **"Enviar a Todos"** to send reminders via API

---

## Need Help?

- Meta WhatsApp Docs: https://developers.facebook.com/docs/whatsapp/cloud-api
- Message Templates Guide: https://developers.facebook.com/docs/whatsapp/message-templates
- Pricing: https://developers.facebook.com/docs/whatsapp/pricing
