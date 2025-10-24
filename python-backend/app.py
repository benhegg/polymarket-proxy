"""
Polymarket Whale Tracker - REST API
FastAPI application serving whale signals and recommendations
"""
import logging
import aiosqlite
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
from datetime import datetime

from config import settings
from models.database import db

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Polymarket Whale Tracker API",
    description="Detects whale activity and generates betting recommendations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.API_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Initializing database...")
    await db.init_db()
    logger.info("API server started successfully")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Polymarket Whale Tracker",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/recommendations")
async def get_recommendations(limit: int = 10) -> Dict[str, Any]:
    """
    Get top whale betting recommendations
    Returns markets ranked by whale score
    """
    try:
        async with aiosqlite.connect(db.db_path) as database:
            database.row_factory = aiosqlite.Row

            # Get active recommendations sorted by whale score
            async with database.execute("""
                SELECT
                    r.id,
                    r.market_id,
                    r.direction,
                    r.whale_score,
                    r.confidence,
                    r.signals_fired,
                    r.created_at,
                    m.question,
                    m.category,
                    m.slug
                FROM recommendations r
                JOIN markets m ON r.market_id = m.id
                WHERE r.is_active = TRUE
                ORDER BY r.whale_score DESC, r.created_at DESC
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                recommendations = [dict(row) for row in rows]

        # Parse signals_fired from JSON string
        for rec in recommendations:
            import json
            rec['signals_fired'] = json.loads(rec.get('signals_fired', '[]'))

        return {
            "count": len(recommendations),
            "recommendations": recommendations,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/signals")
async def get_signals(hours: int = 24, limit: int = 100) -> Dict[str, Any]:
    """
    Get recent whale signals detected
    """
    try:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        async with aiosqlite.connect(db.db_path) as database:
            database.row_factory = aiosqlite.Row

            async with database.execute("""
                SELECT
                    s.id,
                    s.market_id,
                    s.signal_type,
                    s.detected_at,
                    s.value,
                    s.threshold,
                    s.metadata,
                    m.question,
                    m.category
                FROM signals s
                JOIN markets m ON s.market_id = m.id
                WHERE s.detected_at >= ?
                ORDER BY s.detected_at DESC
                LIMIT ?
            """, (cutoff, limit)) as cursor:
                rows = await cursor.fetchall()
                signals = [dict(row) for row in rows]

        # Parse metadata from JSON
        for signal in signals:
            import json
            signal['metadata'] = json.loads(signal.get('metadata', '{}'))

        return {
            "count": len(signals),
            "signals": signals,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/markets")
async def get_markets() -> Dict[str, Any]:
    """
    Get all tracked markets with latest snapshot data
    """
    try:
        async with aiosqlite.connect(db.db_path) as database:
            database.row_factory = aiosqlite.Row

            # Get markets with their latest snapshot
            async with database.execute("""
                SELECT
                    m.id,
                    m.question,
                    m.category,
                    m.slug,
                    s.volume,
                    s.liquidity,
                    s.yes_price,
                    s.no_price,
                    s.timestamp
                FROM markets m
                LEFT JOIN (
                    SELECT market_id, volume, liquidity, yes_price, no_price, timestamp,
                           ROW_NUMBER() OVER (PARTITION BY market_id ORDER BY timestamp DESC) as rn
                    FROM snapshots
                ) s ON m.id = s.market_id AND s.rn = 1
                ORDER BY s.volume DESC
            """) as cursor:
                rows = await cursor.fetchall()
                markets = [dict(row) for row in rows]

        return {
            "count": len(markets),
            "markets": markets,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching markets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/paper-trading/stats")
async def get_paper_trading_stats(days: int = 7) -> Dict[str, Any]:
    """
    Get paper trading performance statistics
    """
    try:
        from services.paper_trader import paper_trader
        stats = await paper_trader.get_performance_stats(days=days)

        return {
            "period_days": days,
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching paper trading stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/paper-trading/positions")
async def get_paper_trading_positions() -> Dict[str, Any]:
    """
    Get open paper trading positions
    """
    try:
        from services.paper_trader import paper_trader
        positions = await paper_trader.get_open_positions()

        return {
            "count": len(positions),
            "positions": positions,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/paper-trading/history")
async def get_paper_trading_history(limit: int = 50) -> Dict[str, Any]:
    """
    Get paper trading history
    """
    try:
        from services.paper_trader import paper_trader
        history = await paper_trader.get_trade_history(limit=limit)

        return {
            "count": len(history),
            "trades": history,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching trade history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/{market_id}/signals")
async def get_market_signals(market_id: str, hours: int = 24) -> Dict[str, Any]:
    """
    Get signals for a specific market
    """
    try:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        async with aiosqlite.connect(db.db_path) as database:
            database.row_factory = aiosqlite.Row

            async with database.execute("""
                SELECT * FROM signals
                WHERE market_id = ? AND detected_at >= ?
                ORDER BY detected_at DESC
            """, (market_id, cutoff)) as cursor:
                rows = await cursor.fetchall()
                signals = [dict(row) for row in rows]

        # Parse metadata
        for signal in signals:
            import json
            signal['metadata'] = json.loads(signal.get('metadata', '{}'))

        return {
            "market_id": market_id,
            "count": len(signals),
            "signals": signals,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching market signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
