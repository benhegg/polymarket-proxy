"""
Telegram Notification Service
Sends alerts for high-confidence whale signals (score >= 75)
"""
import logging
from typing import Dict, Any, List
from config import settings

logger = logging.getLogger(__name__)

# Try to import Telegram - it's optional
try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not installed. Telegram notifications disabled.")


class TelegramNotifier:
    """Sends Telegram notifications for whale alerts"""

    def __init__(self):
        self.enabled = settings.TELEGRAM_ENABLED and TELEGRAM_AVAILABLE
        self.bot = None
        self.chat_id = settings.TELEGRAM_CHAT_ID

        if not TELEGRAM_AVAILABLE and settings.TELEGRAM_ENABLED:
            logger.warning("Telegram is enabled in config but python-telegram-bot is not installed.")
            logger.warning("To enable Telegram: pip install python-telegram-bot")
            self.enabled = False
            return

        if self.enabled and settings.TELEGRAM_BOT_TOKEN:
            try:
                self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
                logger.info("Telegram bot initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
                self.enabled = False

    async def send_whale_alert(self, recommendation: Dict[str, Any]):
        """
        Send whale alert for high-confidence recommendation
        """
        if not self.enabled or not self.bot:
            return

        try:
            whale_score = recommendation.get('whale_score', 0)

            # Only send if high confidence
            if whale_score < settings.HIGH_CONFIDENCE_SCORE:
                return

            # Format message
            message = self._format_alert_message(recommendation)

            # Send message
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )

            logger.info(f"Telegram alert sent for market {recommendation.get('market_id')}")

        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")

    def _format_alert_message(self, rec: Dict[str, Any]) -> str:
        """Format recommendation as Telegram message"""

        # Emoji indicators
        confidence_emoji = {
            'HIGH': '🔥',
            'MEDIUM': '⚡',
            'LOW': '📊'
        }

        direction_emoji = {
            'YES': '🟢',
            'NO': '🔴',
            'NEUTRAL': '⚪'
        }

        confidence = rec.get('confidence', 'UNKNOWN')
        direction = rec.get('direction', 'NEUTRAL')
        whale_score = rec.get('whale_score', 0)
        market_question = rec.get('question', 'Unknown Market')
        signals_fired = rec.get('signals_fired', [])

        # Format signal names for display
        signal_names = {
            'volume_spike': 'Volume Spike 📈',
            'smart_money': 'Smart Money 🧠',
            'book_imbalance': 'Order Book Imbalance ⚖️',
            'liquidity_drain': 'Liquidity Drain 💧',
            'large_order': 'Large Order 🐋'
        }

        signals_text = '\n'.join([f"  • {signal_names.get(s, s)}" for s in signals_fired])

        message = f"""
{confidence_emoji.get(confidence, '📊')} <b>WHALE ALERT</b> {confidence_emoji.get(confidence, '📊')}

<b>Market:</b> {market_question[:100]}

<b>Recommendation:</b> {direction_emoji.get(direction, '⚪')} <b>{direction}</b>
<b>Whale Score:</b> {whale_score}/100
<b>Confidence:</b> {confidence}

<b>Signals Detected:</b>
{signals_text}

<i>Paper trade auto-entered. Check dashboard for details.</i>
        """.strip()

        return message

    async def send_performance_update(self, stats: Dict[str, Any]):
        """Send daily/weekly performance update"""
        if not self.enabled or not self.bot:
            return

        try:
            message = f"""
📊 <b>Paper Trading Performance Update</b>

<b>Last 7 Days:</b>
  • Total Trades: {stats.get('total_trades', 0)}
  • Win Rate: {stats.get('win_rate', 0):.1f}%
  • Total P&L: ${stats.get('total_pnl', 0):+.2f}
  • Avg P&L: ${stats.get('avg_pnl', 0):+.2f}

<b>High-Confidence Trades (Score ≥75):</b>
  • Count: {stats.get('high_score_trades', 0)}
  • Win Rate: {stats.get('high_score_win_rate', 0):.1f}%

<b>Best Trade:</b> ${stats.get('best_trade', {}).get('pnl', 0):+.2f}
<b>Worst Trade:</b> ${stats.get('worst_trade', {}).get('pnl', 0):+.2f}
            """.strip()

            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )

            logger.info("Performance update sent via Telegram")

        except Exception as e:
            logger.error(f"Error sending performance update: {e}")

    async def test_connection(self) -> bool:
        """Test Telegram connection"""
        if not self.enabled or not self.bot:
            return False

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text="🤖 Polymarket Whale Tracker connected successfully!"
            )
            return True
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False


# Global notifier instance
telegram_notifier = TelegramNotifier()
