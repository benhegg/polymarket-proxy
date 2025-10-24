"""
SQLite Database Schema and Connection Management
"""
import aiosqlite
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from config import settings

logger = logging.getLogger(__name__)


class Database:
    """Async SQLite database manager"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DATABASE_PATH

    async def init_db(self):
        """Initialize database schema"""
        async with aiosqlite.connect(self.db_path) as db:
            # Markets table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS markets (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    category TEXT,
                    slug TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Snapshots table - stores 5-minute polling data
            await db.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    volume REAL NOT NULL,
                    liquidity REAL NOT NULL,
                    yes_price REAL NOT NULL,
                    no_price REAL NOT NULL,
                    yes_bid REAL,
                    yes_ask REAL,
                    no_bid REAL,
                    no_ask REAL,
                    buy_orders_count INTEGER DEFAULT 0,
                    sell_orders_count INTEGER DEFAULT 0,
                    total_buy_volume REAL DEFAULT 0,
                    total_sell_volume REAL DEFAULT 0,
                    FOREIGN KEY (market_id) REFERENCES markets(id)
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_market_time ON snapshots(market_id, timestamp DESC)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON snapshots(timestamp DESC)")

            # Signals table - detected whale activity
            await db.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    detected_at TIMESTAMP NOT NULL,
                    value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (market_id) REFERENCES markets(id)
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_signals_market_time ON signals(market_id, detected_at DESC)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(signal_type)")

            # Recommendations table - betting recommendations
            await db.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    whale_score INTEGER NOT NULL,
                    confidence TEXT NOT NULL,
                    signals_fired TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (market_id) REFERENCES markets(id)
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_recs_active_score ON recommendations(is_active, whale_score DESC)")

            # Paper trades table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recommendation_id INTEGER NOT NULL,
                    market_id TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_time TIMESTAMP NOT NULL,
                    exit_price REAL,
                    exit_time TIMESTAMP,
                    bet_size REAL NOT NULL,
                    pnl REAL,
                    is_closed BOOLEAN DEFAULT FALSE,
                    whale_score INTEGER NOT NULL,
                    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id),
                    FOREIGN KEY (market_id) REFERENCES markets(id)
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_paper_trades_active ON paper_trades(is_closed, entry_time DESC)")

            # Performance metrics table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    avg_whale_score REAL DEFAULT 0,
                    best_signal_type TEXT,
                    UNIQUE(date)
                )
            """)

            await db.commit()
            logger.info("Database schema initialized successfully")

    async def cleanup_old_data(self):
        """Remove data older than retention period"""
        cutoff_date = datetime.utcnow() - timedelta(days=settings.DATA_RETENTION_DAYS)

        async with aiosqlite.connect(self.db_path) as db:
            # Clean old snapshots
            await db.execute("DELETE FROM snapshots WHERE timestamp < ?", (cutoff_date,))

            # Clean old signals
            await db.execute("DELETE FROM signals WHERE detected_at < ?", (cutoff_date,))

            # Clean inactive old recommendations
            await db.execute(
                "DELETE FROM recommendations WHERE is_active = FALSE AND created_at < ?",
                (cutoff_date,)
            )

            # Keep all paper trades (for historical performance tracking)

            deleted = db.total_changes
            await db.commit()

            logger.info(f"Cleaned up {deleted} old records (>30 days)")

    async def save_snapshot(self, market_id: str, data: Dict[str, Any]):
        """Save a market snapshot"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO snapshots (
                    market_id, timestamp, volume, liquidity, yes_price, no_price,
                    yes_bid, yes_ask, no_bid, no_ask,
                    buy_orders_count, sell_orders_count,
                    total_buy_volume, total_sell_volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                market_id,
                data.get('timestamp', datetime.utcnow()),
                data.get('volume', 0),
                data.get('liquidity', 0),
                data.get('yes_price', 0),
                data.get('no_price', 0),
                data.get('yes_bid'),
                data.get('yes_ask'),
                data.get('no_bid'),
                data.get('no_ask'),
                data.get('buy_orders_count', 0),
                data.get('sell_orders_count', 0),
                data.get('total_buy_volume', 0),
                data.get('total_sell_volume', 0)
            ))
            await db.commit()

    async def save_signal(self, market_id: str, signal_type: str, value: float, threshold: float, metadata: str = None):
        """Save a detected signal"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO signals (market_id, signal_type, detected_at, value, threshold, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (market_id, signal_type, datetime.utcnow(), value, threshold, metadata))
            await db.commit()

    async def get_recent_snapshots(self, market_id: str, minutes: int = 60) -> List[Dict]:
        """Get snapshots for a market within the specified time window"""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM snapshots
                WHERE market_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (market_id, cutoff)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_latest_snapshot(self, market_id: str) -> Optional[Dict]:
        """Get the most recent snapshot for a market"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM snapshots
                WHERE market_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (market_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None


# Global database instance
db = Database()
