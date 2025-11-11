# Resend.com Setup Guide

## Step 1: Sign Up for Resend (5 minutes)

1. Go to https://resend.com
2. Click "Get Started" or "Sign Up"
3. Create your account (free tier: 3,000 emails/month, 100/day)

## Step 2: Get Your API Key (2 minutes)

1. After logging in, go to **API Keys** in the dashboard
2. Click "Create API Key"
3. Name it: "VueloDigno Production"
4. Copy the API key (starts with `re_...`)

## Step 3: Add Domain (Optional but Recommended)

**Option A: Use Resend's test domain (Quick - 0 min)**
- Email will be from: `onboarding@resend.dev`
- Works immediately, no setup needed
- Good for testing

**Option B: Add your own domain (10 minutes)**
1. In Resend dashboard, go to **Domains**
2. Click "Add Domain"
3. Enter your domain (e.g., `vuelodigno.com`)
4. Add the DNS records they provide to your domain registrar
5. Wait for verification (~5-10 minutes)
6. Email will be from: `noreply@vuelodigno.com`

## Step 4: Set Environment Variable (1 minute)

### On Mac/Linux:
```bash
export RESEND_API_KEY="re_your_api_key_here"
```

To make it permanent, add to your `~/.zshrc` or `~/.bashrc`:
```bash
echo 'export RESEND_API_KEY="re_your_api_key_here"' >> ~/.zshrc
source ~/.zshrc
```

### On Windows:
```powershell
setx RESEND_API_KEY "re_your_api_key_here"
```

## Step 5: Install Resend Package

```bash
pip install resend
```

## Step 6: Update app.py

Replace the import in `app.py`:
```python
# OLD:
from email_sender import send_claim_email

# NEW:
from email_sender_resend import send_claim_email_resend, send_confirmation_to_user
```

Then update the `/send` route to use the new function.

## Step 7: Update email_sender_resend.py

If using your own domain, replace line 24:
```python
"from": "VueloDigno <noreply@vuelodigno.com>",  # Your verified domain
```

If using test domain:
```python
"from": "Delivered via Resend <onboarding@resend.dev>",
```

## Testing

1. Start your Flask app: `python app.py`
2. Fill out the form
3. Click "Enviar Ahora"
4. Check:
   - ✅ Airline receives the email
   - ✅ User gets a copy (CC)
   - ✅ User gets confirmation email
   - ✅ Replies go to user's email (reply_to)

## Troubleshooting

**Error: "RESEND_API_KEY not found"**
- Make sure you exported the environment variable
- Restart your terminal after adding it
- Check: `echo $RESEND_API_KEY`

**Error: "Domain not verified"**
- Use test domain (`onboarding@resend.dev`) for now
- Or wait for DNS verification (can take up to 24 hours)

**Emails going to spam:**
- This is normal with new domains
- Verify your domain's SPF/DKIM records
- Use a custom domain (not test domain)
- Build sending reputation over time

## Free Tier Limits

- ✅ 3,000 emails/month
- ✅ 100 emails/day
- ✅ Unlimited domains
- ✅ All features included

Perfect for testing and early users!
