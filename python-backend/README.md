# Polymarket Whale Tracker - Python Backend

Detects whale activity on Polymarket and generates high-confidence betting recommendations based on 5 statistical signals.

## Features

### 🐋 Whale Signal Detection
1. **Volume Spikes** - Detects >5x normal volume in 5 minutes
2. **Smart Money Accumulation** - High volume (>$50k) with minimal price movement (<2%)
3. **Order Book Imbalance** - 70%+ one-sided order flow
4. **Liquidity Drains** - >20% liquidity decrease (market makers pulling out)
5. **Large Orders** - Individual trades >$50k

### 📊 Whale Score System
- 0-100 confidence score based on signal strength
- Weighted scoring (Volume Spike: 30pts, Smart Money: 25pts, etc.)
- Signal intensity multipliers for extreme values

### 📈 Paper Trading Tracker
- Auto-enters paper trades for high-confidence signals (score ≥75)
- Tracks P&L and win rates
- 24-hour holding period
- Performance metrics by signal type

### 📱 Telegram Alerts
- Real-time notifications for score ≥75 recommendations
- Daily performance updates
- Customizable alert thresholds

## Architecture

```
┌─────────────────────────────────────────┐
│ Poller (Every 5 min)                    │
│  → Fetch Polymarket data                │
│  → Detect signals                       │
│  → Calculate whale scores               │
│  → Generate recommendations             │
│  → Auto-enter paper trades              │
│  → Send Telegram alerts                 │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│ SQLite Database                         │
│  → Markets, Snapshots, Signals          │
│  → Recommendations, Paper Trades        │
│  → 30-day retention                     │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│ FastAPI REST API                        │
│  → GET /api/recommendations             │
│  → GET /api/signals                     │
│  → GET /api/paper-trading/stats         │
└─────────────────────────────────────────┘
```

## Quick Start

### Option 1: Local Development

```bash
# 1. Navigate to python-backend directory
cd python-backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment template
cp .env.example .env

# 4. (Optional) Configure Telegram in .env
# TELEGRAM_ENABLED=true
# TELEGRAM_BOT_TOKEN=your_token
# TELEGRAM_CHAT_ID=your_chat_id

# 5. Run the system
python poller.py &    # Start background poller
python app.py         # Start API server
```

The API will be available at `http://localhost:8000`

### Option 2: Docker

```bash
# Build and run
docker build -t whale-tracker .
docker run -p 8000:8000 -v $(pwd)/data:/app/data whale-tracker
```

### Option 3: Deploy to Railway

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Initialize project
railway init

# 4. Deploy
railway up

# 5. Set environment variables (optional)
railway variables set TELEGRAM_ENABLED=true
railway variables set TELEGRAM_BOT_TOKEN=your_token
railway variables set TELEGRAM_CHAT_ID=your_chat_id
```

### Option 4: Deploy to Render

1. Connect your GitHub repo to Render
2. Create new Web Service
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python -m uvicorn app:app --host 0.0.0.0 --port $PORT & python poller.py`
5. Add environment variables (optional):
   - `TELEGRAM_ENABLED=true`
   - `TELEGRAM_BOT_TOKEN=your_token`
   - `TELEGRAM_CHAT_ID=your_chat_id`

## API Endpoints

### GET /api/recommendations
Returns top 10 whale betting recommendations ranked by score.

**Response:**
```json
{
  "count": 10,
  "recommendations": [
    {
      "id": 1,
      "market_id": "...",
      "question": "Will Trump win 2024?",
      "direction": "YES",
      "whale_score": 85,
      "confidence": "HIGH",
      "signals_fired": ["volume_spike", "smart_money", "book_imbalance"]
    }
  ]
}
```

### GET /api/signals
Returns recent whale signals detected across all markets.

**Parameters:**
- `hours` - Lookback period (default: 24)
- `limit` - Max results (default: 100)

### GET /api/paper-trading/stats
Returns paper trading performance statistics.

**Parameters:**
- `days` - Lookback period (default: 7)

**Response:**
```json
{
  "stats": {
    "total_trades": 45,
    "win_rate": 62.2,
    "total_pnl": 145.80,
    "avg_pnl": 3.24,
    "high_score_win_rate": 71.4
  }
}
```

### GET /api/paper-trading/positions
Returns open paper trading positions.

### GET /api/paper-trading/history
Returns closed paper trade history.

### GET /api/markets
Returns all tracked markets with latest data.

### GET /health
Health check endpoint.

## Configuration

All configuration is in `config.py`. Override via environment variables:

### Signal Thresholds
```env
VOLUME_SPIKE_MULTIPLIER=5.0           # 5x volume spike
SMART_MONEY_MIN_VOLUME=50000.0        # $50k threshold
ORDER_BOOK_IMBALANCE_THRESHOLD=0.70   # 70% imbalance
LIQUIDITY_DRAIN_THRESHOLD_PCT=20.0    # 20% drain
LARGE_ORDER_THRESHOLD=50000.0         # $50k order
```

### Whale Score Weights
```env
SCORE_WEIGHT_VOLUME_SPIKE=30
SCORE_WEIGHT_SMART_MONEY=25
SCORE_WEIGHT_BOOK_IMBALANCE=20
SCORE_WEIGHT_LIQUIDITY_DRAIN=15
SCORE_WEIGHT_LARGE_ORDER=10
```

### Paper Trading
```env
PAPER_TRADING_ENABLED=true
PAPER_TRADE_AUTO_ENTER=true  # Auto-enter for score ≥75
PAPER_TRADE_AMOUNT=100.0
PAPER_TRADE_HOLD_HOURS=24
```

### Market Filters
```env
MIN_MARKET_VOLUME=500000.0   # Only track markets >$500k
```

## Telegram Setup (Optional)

1. Create a Telegram bot via [@BotFather](https://t.me/botfather)
2. Get your bot token
3. Get your chat ID (send a message to your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates`)
4. Set environment variables:
```env
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789
```

## Database Schema

- **markets** - Market metadata
- **snapshots** - 5-minute polling data
- **signals** - Detected whale signals
- **recommendations** - Betting recommendations
- **paper_trades** - Paper trading positions
- **performance_metrics** - Aggregated stats

Data is automatically cleaned after 30 days.

## Integration with Vercel Frontend

The Vercel frontend will fetch from your deployed Python backend:

```javascript
// In your Vercel frontend
const PYTHON_API = 'https://your-railway-or-render-url.com';

// Fetch recommendations
const recommendations = await fetch(`${PYTHON_API}/api/recommendations`);

// Fetch signals
const signals = await fetch(`${PYTHON_API}/api/signals?hours=24`);

// Fetch paper trading stats
const stats = await fetch(`${PYTHON_API}/api/paper-trading/stats`);
```

## Monitoring

- Check logs: `tail -f app.log`
- View polling cycles in console output
- Monitor paper trading performance via `/api/paper-trading/stats`

## Troubleshooting

**No signals detected:**
- Reduce `MIN_WHALE_SCORE` threshold
- Check `MIN_MARKET_VOLUME` filter
- Lower signal thresholds

**Too many false signals:**
- Increase `MIN_WHALE_SCORE` (e.g., 60+)
- Increase signal thresholds
- Adjust score weights

**API errors:**
- Check Polymarket API status
- Verify rate limits not exceeded
- Review logs for specific errors

## Development

Run tests:
```bash
pytest tests/
```

Format code:
```bash
black .
```

## License

MIT
