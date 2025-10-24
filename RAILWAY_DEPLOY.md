# 🚂 Railway Deployment Guide - Step by Step

Choose the method that works best for you:

---

## ✨ Method 1: Web UI (Recommended - No Installation Required)

### Step 1: Go to Railway
Visit: **https://railway.app/**

### Step 2: Create Account & Start Project
1. Click **"Start a New Project"**
2. Sign in with your **GitHub account**
3. Authorize Railway to access your repositories

### Step 3: Deploy from GitHub
1. Click **"Deploy from GitHub repo"**
2. Select repository: **`benhegg/polymarket-proxy`**
3. Select branch: **`claude/polymarket-data-polling-011CUPBFTqPCvenKT6Uon76S`**
4. Click **"Deploy Now"**

### Step 4: Configure Project Settings

Railway will start deploying, but we need to configure it:

1. Click on your **service card** in the dashboard
2. Go to **"Settings"** tab (left sidebar)
3. Scroll to **"Root Directory"**
4. Enter: `python-backend`
5. Click **"Update"** (Railway will redeploy automatically)

### Step 5: Verify Build

Watch the deployment logs:
- Click **"Deployments"** tab
- Click the latest deployment
- Watch logs for: `✅ Database schema initialized successfully`
- Wait for: `Build successful` and `Deployment successful`

### Step 6: Generate Domain

1. Go back to **"Settings"** tab
2. Scroll to **"Networking"** section
3. Click **"Generate Domain"**
4. Copy the URL (example: `https://polymarket-whale-tracker-production.up.railway.app`)

### Step 7: Test Your Backend

Open in browser or use curl:
```bash
curl https://your-railway-url.railway.app/health
```

Should return:
```json
{"status":"healthy","timestamp":"2024-10-24T..."}
```

### Step 8: Configure Frontend

1. Go to your Vercel site: `https://your-site.vercel.app/index-whale.html`
2. Click **"⚙️ Config"** button
3. Paste your Railway URL: `https://your-railway-url.railway.app`
4. Click **"Save & Reload"**
5. Wait 30 seconds for first poll to complete
6. Refresh page - **whale recommendations should appear!** 🐋

---

## 🖥️ Method 2: Railway CLI (For Developers)

### Prerequisites
- Node.js installed
- Git installed
- Terminal access

### Step 1: Clone and Navigate
```bash
# Clone your repo
git clone https://github.com/benhegg/polymarket-proxy.git
cd polymarket-proxy

# Switch to deployment branch
git checkout claude/polymarket-data-polling-011CUPBFTqPCvenKT6Uon76S

# Navigate to Python backend
cd python-backend
```

### Step 2: Quick Deploy Script
```bash
# Use the provided deploy script
chmod +x deploy-railway.sh
./deploy-railway.sh
```

**OR manually:**

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login
# (Opens browser for authentication)

# Initialize project
railway init
# Choose: "Create new project"
# Name it: "polymarket-whale-tracker"

# Deploy
railway up
# Uploads code and starts deployment

# Get your URL
railway domain
# Copy the URL shown
```

### Step 3: Set Environment Variables (Optional)

If you want Telegram notifications:
```bash
railway variables set TELEGRAM_ENABLED=true
railway variables set TELEGRAM_BOT_TOKEN=your_token_here
railway variables set TELEGRAM_CHAT_ID=your_chat_id_here
```

### Step 4: View Logs
```bash
railway logs
# Watch real-time logs to verify polling is working
```

---

## 🔧 Troubleshooting

### Issue: "Build Failed"
**Solution:**
1. Go to Settings → "Root Directory"
2. Make sure it's set to: `python-backend`
3. Redeploy

### Issue: "Application Failed to Start"
**Solution:**
1. Check deployment logs for errors
2. Verify all files are in `python-backend/` folder
3. Check that `requirements.txt` exists

### Issue: "No whale recommendations showing"
**Possible causes:**
1. **Backend not responding**: Test `/health` endpoint
2. **Frontend URL wrong**: Check Config has correct Railway URL
3. **No signals yet**: Wait 5-10 minutes for first poll cycle
4. **Markets below threshold**: No markets >$500k volume currently

**Debug steps:**
```bash
# Test recommendations endpoint
curl https://your-railway-url.railway.app/api/recommendations

# Test paper trading stats
curl https://your-railway-url.railway.app/api/paper-trading/stats

# Check health
curl https://your-railway-url.railway.app/health
```

### Issue: "Railway says 'Deployment Crashed'"
**Check logs for:**
- Missing dependencies: `ModuleNotFoundError`
- Port issues: Make sure using `$PORT` environment variable
- Database errors: Check SQLite path is writable

**Solution:**
Railway should auto-detect Python and install dependencies, but if not:
1. Go to Settings → "Start Command"
2. Set: `python -m uvicorn app:app --host 0.0.0.0 --port $PORT & python poller.py`

---

## 📊 Verify Everything is Working

### 1. Check Backend Health
```bash
curl https://your-railway-url.railway.app/health
# Expected: {"status":"healthy",...}
```

### 2. Check Recommendations API
```bash
curl https://your-railway-url.railway.app/api/recommendations
# Expected: {"count": 0, ...} (0 is normal at first)
```

### 3. Check Logs in Railway
Look for these messages:
```
✅ Database schema initialized successfully
🔍 Starting Polymarket Poller...
⏱️ Poller started - running every 300s (5 minutes)
📊 Fetched X markets above $500,000 volume
```

### 4. Check Frontend
1. Visit: `https://your-vercel-site.vercel.app/index-whale.html`
2. Click Config, enter Railway URL, save
3. Wait 5 minutes
4. Refresh page
5. Should see: Paper trading stats + Top whale recommendations

---

## 💰 Railway Pricing

- **Starter Plan**: $5/month
- **Trial Credits**: $5 free on signup (no credit card required)
- **Usage-based**: Only pay for what you use

This app uses minimal resources:
- Runs 24/7
- Polls every 5 minutes
- Uses ~512MB RAM
- Should cost ~$5-10/month

---

## 🎉 Success Checklist

- [ ] Railway project created
- [ ] Code deployed from GitHub
- [ ] Root directory set to `python-backend`
- [ ] Deployment successful (check logs)
- [ ] Domain generated
- [ ] `/health` endpoint responds
- [ ] Frontend configured with Railway URL
- [ ] Whale recommendations appearing (wait 5-10 min)

---

## 📞 Need Help?

**Railway Support:**
- Docs: https://docs.railway.app/
- Discord: https://discord.gg/railway
- Status: https://status.railway.app/

**Check Your Deployment:**
1. Railway Dashboard → Your Project
2. Click "Deployments"
3. Click latest deployment
4. Review logs for errors

---

## 🔄 Updating Your Deployment

When you push new code to GitHub:
1. Railway auto-deploys if connected to GitHub
2. Or run: `railway up` (if using CLI)
3. Changes go live in ~2-3 minutes

---

**Once deployed, your whale tracker runs 24/7 detecting signals every 5 minutes!** 🐋📈
