"""
Paper Trading Tracker
Tracks hypothetical trades to validate signal performance before live trading
"""
import aiosqlite
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from config import settings, Direction

logger = logging.getLogger(__name__)


class PaperTrader:
    """Manages paper trading positions and performance tracking"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DATABASE_PATH

    async def enter_paper_trade(
        self,
        recommendation_id: int,
        market_id: str,
        direction: str,
        entry_price: float,
        whale_score: int,
        bet_size: float = None
    ) -> int:
        """
        Enter a paper trade position
        Returns paper_trade_id
        """
        bet_size = bet_size or settings.PAPER_TRADE_AMOUNT

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO paper_trades (
                    recommendation_id, market_id, direction, entry_price,
                    entry_time, bet_size, whale_score, is_closed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recommendation_id,
                market_id,
                direction,
                entry_price,
                datetime.utcnow(),
                bet_size,
                whale_score,
                False
            ))

            await db.commit()
            paper_trade_id = cursor.lastrowid

            logger.info(
                f"Paper trade opened: ID={paper_trade_id}, "
                f"Market={market_id}, Direction={direction}, "
                f"Entry=${entry_price:.3f}, Score={whale_score}"
            )

            return paper_trade_id

    async def close_paper_trade(
        self,
        paper_trade_id: int,
        exit_price: float
    ):
        """
        Close a paper trade and calculate P&L
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Get trade details
            async with db.execute(
                "SELECT * FROM paper_trades WHERE id = ?",
                (paper_trade_id,)
            ) as cursor:
                trade = await cursor.fetchone()

            if not trade:
                logger.error(f"Paper trade {paper_trade_id} not found")
                return

            # Calculate P&L
            entry_price = trade['entry_price']
            direction = trade['direction']
            bet_size = trade['bet_size']

            if direction == Direction.YES:
                # For YES bets: profit if price goes up
                pnl = (exit_price - entry_price) * bet_size
            elif direction == Direction.NO:
                # For NO bets: profit if price goes down
                pnl = (entry_price - exit_price) * bet_size
            else:
                pnl = 0

            # Update trade with exit info
            await db.execute("""
                UPDATE paper_trades
                SET exit_price = ?, exit_time = ?, pnl = ?, is_closed = ?
                WHERE id = ?
            """, (exit_price, datetime.utcnow(), pnl, True, paper_trade_id))

            await db.commit()

            logger.info(
                f"Paper trade closed: ID={paper_trade_id}, "
                f"Exit=${exit_price:.3f}, P&L=${pnl:+.2f}"
            )

    async def auto_close_expired_trades(self, current_prices: Dict[str, float]):
        """
        Automatically close paper trades that have exceeded hold time
        """
        hold_threshold = datetime.utcnow() - timedelta(hours=settings.PAPER_TRADE_HOLD_HOURS)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Find expired open trades
            async with db.execute("""
                SELECT * FROM paper_trades
                WHERE is_closed = FALSE AND entry_time <= ?
            """, (hold_threshold,)) as cursor:
                expired_trades = await cursor.fetchall()

            for trade in expired_trades:
                market_id = trade['market_id']
                exit_price = current_prices.get(market_id)

                if exit_price is not None:
                    await self.close_paper_trade(trade['id'], exit_price)
                else:
                    logger.warning(f"No current price for market {market_id}, skipping auto-close")

    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open paper trade positions"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute("""
                SELECT pt.*, m.question
                FROM paper_trades pt
                JOIN markets m ON pt.market_id = m.id
                WHERE pt.is_closed = FALSE
                ORDER BY pt.entry_time DESC
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_performance_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Calculate performance statistics
        Returns win rate, total P&L, avg P&L, etc.
        """
        lookback_date = datetime.utcnow() - timedelta(days=days)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Get closed trades within lookback period
            async with db.execute("""
                SELECT * FROM paper_trades
                WHERE is_closed = TRUE AND exit_time >= ?
            """, (lookback_date,)) as cursor:
                trades = await cursor.fetchall()

            if not trades:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0,
                    'best_trade': None,
                    'worst_trade': None,
                    'avg_whale_score': 0,
                    'high_score_win_rate': 0,  # Win rate for scores >= 75
                }

            # Calculate stats
            total_trades = len(trades)
            winning_trades = sum(1 for t in trades if t['pnl'] > 0)
            losing_trades = sum(1 for t in trades if t['pnl'] < 0)
            total_pnl = sum(t['pnl'] for t in trades)
            avg_pnl = total_pnl / total_trades if total_trades > 0 else 0

            best_trade = max(trades, key=lambda t: t['pnl'])
            worst_trade = min(trades, key=lambda t: t['pnl'])

            avg_whale_score = sum(t['whale_score'] for t in trades) / total_trades if total_trades > 0 else 0

            # High-confidence trades (score >= 75)
            high_score_trades = [t for t in trades if t['whale_score'] >= 75]
            high_score_wins = sum(1 for t in high_score_trades if t['pnl'] > 0)
            high_score_win_rate = (high_score_wins / len(high_score_trades) * 100) if high_score_trades else 0

            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                'total_pnl': round(total_pnl, 2),
                'avg_pnl': round(avg_pnl, 2),
                'best_trade': {
                    'pnl': round(best_trade['pnl'], 2),
                    'market_id': best_trade['market_id'],
                    'whale_score': best_trade['whale_score']
                },
                'worst_trade': {
                    'pnl': round(worst_trade['pnl'], 2),
                    'market_id': worst_trade['market_id'],
                    'whale_score': worst_trade['whale_score']
                },
                'avg_whale_score': round(avg_whale_score, 1),
                'high_score_win_rate': round(high_score_win_rate, 1),
                'high_score_trades': len(high_score_trades),
            }

    async def get_trade_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trade history"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute("""
                SELECT pt.*, m.question
                FROM paper_trades pt
                JOIN markets m ON pt.market_id = m.id
                WHERE pt.is_closed = TRUE
                ORDER BY pt.exit_time DESC
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


# Global paper trader instance
paper_trader = PaperTrader()
