# Polymarket Whale Tracker - Complete Setup Guide

This project now includes a Python backend for whale signal detection alongside the existing Vercel frontend.

## Architecture

```
┌──────────────────────────────────────────────────┐
│ VERCEL FRONTEND                                   │
│ - index.html: Original markets view              │
│ - index-whale.html: NEW whale signals dashboard  │
└──────────────────────────────────────────────────┘
                    ↓ Fetches via HTTP
┌──────────────────────────────────────────────────┐
│ PYTHON BACKEND (Deploy separately)               │
│ - Polls Polymarket every 5 minutes               │
│ - Detects whale signals                          │
│ - Generates recommendations                      │
│ - Tracks paper trading P&L                       │
│ - Sends Telegram alerts                          │
└──────────────────────────────────────────────────┘
```

## Quick Start

### Step 1: Deploy Python Backend

Choose one deployment option:

#### Option A: Railway (Recommended)
```bash
cd python-backend
railway login
railway init
railway up

# After deployment, Railway will give you a URL like:
# https://your-app.railway.app
```

#### Option B: Render
1. Push code to GitHub
2. Go to render.com
3. Create new Web Service
4. Connect your repo
5. Set: `python-backend` as root directory
6. Use deployment config from `python-backend/deployment/render.yaml`

#### Option C: Local Development
```bash
cd python-backend
pip install -r requirements.txt
chmod +x start.sh
./start.sh

# Backend runs at http://localhost:8000
```

### Step 2: Update Vercel Frontend

**Option A: Use Enhanced Whale Dashboard**
```bash
# Rename the new whale dashboard to be the main page
mv index.html index-original.html
mv index-whale.html index.html

# Commit and push
git add .
git commit -m "Enable whale tracker dashboard"
git push
```

**Option B: Keep Both Pages**
- Original markets view: `https://your-site.vercel.app/` (index.html)
- Whale tracker: `https://your-site.vercel.app/index-whale.html`

### Step 3: Configure Frontend

1. Visit your Vercel site
2. Click "⚙️ Config" button
3. Enter your Python backend URL:
   - Railway: `https://your-app.railway.app`
   - Render: `https://your-app.onrender.com`
   - Local: `http://localhost:8000`
4. Click "Save & Reload"

That's it! The whale tracker should now display recommendations.

## Features You Get

### 🐋 5 Whale Signals
1. **Volume Spike** - 5x normal volume detected
2. **Smart Money** - High volume + low price movement (whales accumulating)
3. **Order Book Imbalance** - 70%+ one-sided pressure
4. **Liquidity Drain** - Market makers pulling out
5. **Large Orders** - Individual trades >$50k

### 📊 Whale Score (0-100)
- Weighted combination of all signals
- HIGH confidence: 75-100 (auto-enter paper trades + Telegram alerts)
- MEDIUM confidence: 50-74
- LOW confidence: 25-49

### 📈 Paper Trading
- Automatically tracks hypothetical trades
- 24-hour holding period
- Win rate and P&L tracking
- Validates signals before live trading

### 📱 Telegram Alerts (Optional)
- Real-time notifications for high-confidence signals (score ≥75)
- Daily performance summaries

## Optional: Enable Telegram Alerts

### 1. Create Telegram Bot
```
1. Message @BotFather on Telegram
2. Send: /newbot
3. Follow prompts to create bot
4. Save the bot token (looks like: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11)
```

### 2. Get Your Chat ID
```
1. Message your bot (any message)
2. Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
3. Find your chat ID in the JSON response
```

### 3. Configure Backend
```bash
# If using Railway/Render, set environment variables:
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# If running locally, edit python-backend/.env:
cp .env.example .env
# Edit .env with your values
```

## Monitoring & Debugging

### Check Backend Health
```bash
curl https://your-backend-url.railway.app/health
```

### View Recommendations API
```bash
curl https://your-backend-url.railway.app/api/recommendations
```

### View Paper Trading Stats
```bash
curl https://your-backend-url.railway.app/api/paper-trading/stats
```

### Backend Logs
- **Railway**: View in Railway dashboard
- **Render**: View in Render dashboard
- **Local**: Check terminal output

## Customization

### Adjust Signal Thresholds

Edit `python-backend/config.py` or set environment variables:

```env
# More sensitive (more signals)
VOLUME_SPIKE_MULTIPLIER=3.0
SMART_MONEY_MIN_VOLUME=25000.0

# Less sensitive (fewer false positives)
VOLUME_SPIKE_MULTIPLIER=7.0
SMART_MONEY_MIN_VOLUME=100000.0
```

### Adjust Whale Score Weights

```env
SCORE_WEIGHT_VOLUME_SPIKE=35  # Increase volume spike importance
SCORE_WEIGHT_SMART_MONEY=30   # Increase smart money importance
```

### Filter Markets

```env
MIN_MARKET_VOLUME=1000000.0   # Only track markets >$1M
```

## Troubleshooting

**Problem: "Configure Python API URL to see whale recommendations"**
- Solution: Click ⚙️ Config and enter your Python backend URL

**Problem: No recommendations showing**
- Check backend is running: `curl https://your-backend-url/health`
- Verify markets meet minimum volume threshold ($500k default)
- Wait 5-10 minutes for first poll to complete
- Check backend logs for errors

**Problem: Frontend can't connect to backend**
- Check CORS is enabled in backend (it is by default)
- Verify backend URL is correct (no trailing slash)
- Check browser console for errors (F12)

**Problem: Too many false signals**
- Increase `MIN_WHALE_SCORE` in config.py (default: 50)
- Adjust signal thresholds to be more strict

## Architecture Details

### Data Flow
```
1. Poller runs every 5 minutes
2. Fetches markets from Polymarket (Gamma, CLOB, Data APIs)
3. Saves snapshot to SQLite
4. Runs 5 signal detection algorithms
5. Calculates whale score (0-100)
6. Generates top 10 recommendations
7. Auto-enters paper trades for score ≥75
8. Sends Telegram alerts
9. Frontend fetches recommendations via REST API
10. Displays in clean cards
```

### Database (SQLite)
- 30-day data retention
- ~288 snapshots per market per day (every 5 min)
- Stores: markets, snapshots, signals, recommendations, paper_trades

## Development

See `python-backend/README.md` for detailed backend documentation.

## Support

- Backend issues: Check `python-backend/README.md`
- Frontend issues: Check browser console (F12)
- API errors: Check backend logs

## License

MIT
