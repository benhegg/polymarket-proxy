"""
Background Polling Service
Runs every 5 minutes to collect data, detect signals, and generate recommendations
"""
import asyncio
import logging
import aiosqlite
import json
from datetime import datetime
from typing import List, Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import settings, Direction
from models.database import db
from services.polymarket_client import polymarket_client
from services.signal_detector import signal_detector
from services.whale_scorer import whale_scorer
from services.paper_trader import paper_trader
from services.telegram_notifier import telegram_notifier

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PolymarketPoller:
    """Background service that polls Polymarket and processes data"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    async def poll_and_analyze(self):
        """Main polling function - runs every 5 minutes"""
        try:
            logger.info("=" * 60)
            logger.info("Starting polling cycle...")
            start_time = datetime.utcnow()

            # Step 1: Fetch active markets
            markets = await polymarket_client.get_active_markets()
            if not markets:
                logger.warning("No markets fetched, skipping cycle")
                return

            logger.info(f"Fetched {len(markets)} markets above ${settings.MIN_MARKET_VOLUME:,.0f} volume")

            # Step 2: Process each market
            all_recommendations = []

            for market in markets:
                try:
                    await self._process_market(market, all_recommendations)
                except Exception as e:
                    logger.error(f"Error processing market {market.get('id')}: {e}")
                    continue

            # Step 3: Save top recommendations to database
            await self._save_recommendations(all_recommendations)

            # Step 4: Auto-close expired paper trades
            await self._manage_paper_trades(markets)

            # Step 5: Cleanup old data
            if datetime.utcnow().hour == 0:  # Daily at midnight
                await db.cleanup_old_data()

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Polling cycle completed in {elapsed:.1f}s")
            logger.info(f"Generated {len(all_recommendations)} recommendations")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error in polling cycle: {e}", exc_info=True)

    async def _process_market(self, market: Dict[str, Any], recommendations_list: List):
        """Process a single market: enrich, save, detect signals, score"""
        market_id = market.get('id')

        # Enrich with order book data
        enriched_data = await polymarket_client.enrich_market_data(market)

        # Save market metadata if not exists
        await self._ensure_market_exists(market)

        # Save snapshot
        await db.save_snapshot(market_id, enriched_data)

        # Detect signals
        signals = await signal_detector.detect_all_signals(market_id, enriched_data)

        if not signals:
            return  # No signals, skip this market

        # Calculate whale score
        score_data = whale_scorer.calculate_score(signals)

        # Skip if score too low
        if score_data['whale_score'] < settings.MIN_WHALE_SCORE:
            return

        # Determine betting direction
        direction = signal_detector.determine_direction(
            signals,
            enriched_data.get('yes_price', 0.5)
        )

        # Create recommendation
        recommendation = {
            'market_id': market_id,
            'question': market.get('question'),
            'category': market.get('category'),
            'slug': market.get('slug'),
            'direction': direction,
            'whale_score': score_data['whale_score'],
            'confidence': score_data['confidence'],
            'signals_fired': score_data['signals_fired'],
            'current_price': enriched_data.get('yes_price', 0.5),
            'volume': enriched_data.get('volume', 0),
            'liquidity': enriched_data.get('liquidity', 0),
        }

        recommendations_list.append(recommendation)

        logger.info(
            f"🐋 Market: {market.get('question')[:60]}... | "
            f"Score: {score_data['whale_score']}/100 | "
            f"Direction: {direction} | "
            f"Signals: {len(signals)}"
        )

    async def _ensure_market_exists(self, market: Dict[str, Any]):
        """Save market to database if it doesn't exist"""
        async with aiosqlite.connect(db.db_path) as database:
            await database.execute("""
                INSERT OR REPLACE INTO markets (id, question, category, slug, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                market.get('id'),
                market.get('question'),
                market.get('category'),
                market.get('slug'),
                datetime.utcnow()
            ))
            await database.commit()

    async def _save_recommendations(self, recommendations: List[Dict[str, Any]]):
        """
        Save recommendations to database
        Deactivate old recommendations and create new ones
        """
        if not recommendations:
            return

        # Sort and filter top recommendations
        top_recommendations = whale_scorer.filter_recommendations(recommendations)

        async with aiosqlite.connect(db.db_path) as database:
            # Deactivate all old recommendations
            await database.execute("UPDATE recommendations SET is_active = FALSE")

            # Insert new recommendations
            for rec in top_recommendations:
                cursor = await database.execute("""
                    INSERT INTO recommendations (
                        market_id, direction, whale_score, confidence,
                        signals_fired, created_at, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    rec['market_id'],
                    rec['direction'],
                    rec['whale_score'],
                    rec['confidence'],
                    json.dumps(rec['signals_fired']),
                    datetime.utcnow(),
                    True
                ))

                recommendation_id = cursor.lastrowid

                # Auto-enter paper trade if high confidence
                if rec['whale_score'] >= settings.HIGH_CONFIDENCE_SCORE:
                    if settings.PAPER_TRADING_ENABLED and settings.PAPER_TRADE_AUTO_ENTER:
                        await paper_trader.enter_paper_trade(
                            recommendation_id=recommendation_id,
                            market_id=rec['market_id'],
                            direction=rec['direction'],
                            entry_price=rec['current_price'],
                            whale_score=rec['whale_score']
                        )

                        # Send Telegram alert
                        await telegram_notifier.send_whale_alert(rec)

            await database.commit()

        logger.info(f"Saved {len(top_recommendations)} recommendations to database")

    async def _manage_paper_trades(self, markets: List[Dict[str, Any]]):
        """Manage paper trading: close expired positions"""
        if not settings.PAPER_TRADING_ENABLED:
            return

        # Build dict of current prices
        current_prices = {}
        for market in markets:
            try:
                outcome_prices = market.get('outcomePrices')
                if isinstance(outcome_prices, str):
                    outcome_prices = json.loads(outcome_prices)
                yes_price = float(outcome_prices[0]) if outcome_prices else 0.5
                current_prices[market['id']] = yes_price
            except:
                continue

        # Close expired trades
        await paper_trader.auto_close_expired_trades(current_prices)

    def start(self):
        """Start the polling scheduler"""
        logger.info("Starting Polymarket Poller...")

        # Schedule polling every 5 minutes
        self.scheduler.add_job(
            self.poll_and_analyze,
            trigger=IntervalTrigger(seconds=settings.POLL_INTERVAL_SECONDS),
            id='polymarket_poll',
            name='Poll Polymarket APIs',
            replace_existing=True
        )

        # Run first poll immediately
        self.scheduler.add_job(
            self.poll_and_analyze,
            id='initial_poll',
            name='Initial Poll'
        )

        self.scheduler.start()
        logger.info(f"Poller started - running every {settings.POLL_INTERVAL_SECONDS}s (5 minutes)")

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Poller stopped")


async def main():
    """Main entry point for standalone poller"""
    # Initialize database
    logger.info("Initializing database...")
    await db.init_db()

    # Create and start poller
    poller = PolymarketPoller()
    poller.start()

    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        poller.stop()


if __name__ == "__main__":
    asyncio.run(main())
