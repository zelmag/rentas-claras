# Deployment Guide for VueloDigno

## Quick Fix: Get Your Site Back Online

Your site is returning 503 errors because the Vercel deployment is not active. Follow these steps:

### Option 1: Deploy via Vercel CLI (Fastest)

1. **Install Vercel CLI** (if not already installed):
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**:
   ```bash
   vercel login
   ```
   This will open your browser for authentication.

3. **Deploy from project directory**:
   ```bash
   cd /Users/zelma/Desktop/ZelmaHelps_Agent
   vercel --prod
   ```

4. **Set Environment Variables** (CRITICAL):
   ```bash
   vercel env add RESEND_API_KEY
   # When prompted, paste: re_eM3juG4m_At9ydx1n95pQf4RRTKd8Mkc7

   vercel env add FROM_EMAIL
   # When prompted, paste: reclamos@vuelodigno.com
   ```

5. **Redeploy to apply environment variables**:
   ```bash
   vercel --prod
   ```

6. **Link your domain** (if not already linked):
   ```bash
   vercel domains add vuelodigno.com
   ```

---

### Option 2: Deploy via Vercel Dashboard (Easier if you prefer UI)

1. Go to https://vercel.com/dashboard
2. Click "Add New..." → "Project"
3. Import your GitHub repository (or upload files)
4. Configure:
   - **Framework Preset**: Other
   - **Build Command**: (leave empty)
   - **Output Directory**: (leave empty)
   - **Install Command**: `pip install -r requirements.txt`
5. Add Environment Variables:
   - `RESEND_API_KEY` = `<your-resend-api-key-here>`
   - `FROM_EMAIL` = `reclamos@vuelodigno.com`
6. Click "Deploy"
7. Once deployed, go to "Settings" → "Domains" and add `vuelodigno.com`

---

### Option 3: Automated Script

Run the deployment script:
```bash
./deploy.sh
```

---

## Troubleshooting

### If the site still shows 503 after deployment:

1. **Check deployment logs**:
   ```bash
   vercel logs
   ```

2. **Verify environment variables are set**:
   ```bash
   vercel env ls
   ```

3. **Check domain configuration**:
   - Go to your domain registrar (e.g., GoDaddy, Namecheap)
   - Ensure DNS points to Vercel's servers
   - Vercel will provide nameservers or A/CNAME records to use

4. **Verify Resend domain**:
   - Log into https://resend.com/
   - Ensure `vuelodigno.com` is verified
   - Check DNS records are properly configured

### If you get "command not found: npm":

Install Node.js first:
- Download from: https://nodejs.org/
- Then install Vercel CLI: `npm install -g vercel`

---

## What's Been Fixed

✅ Updated `vercel.json` with proper Flask configuration
✅ Added static file routing
✅ Environment variables identified
✅ All dependencies verified

## Next Steps After Deployment

1. Test the site: https://vuelodigno.com
2. Submit a test claim to verify email sending works
3. Monitor logs for any errors
4. Set up monitoring/alerts in Vercel dashboard

---

## Emergency Contact

If deployment fails:
- Vercel Support: https://vercel.com/support
- Check deployment status: https://vercel.com/dashboard
