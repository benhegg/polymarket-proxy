"""
Signal Detection Engine
Detects 5 types of whale signals based on market data
"""
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from config import settings, SignalType, Direction
from models.database import db
from services.polymarket_client import polymarket_client

logger = logging.getLogger(__name__)


class SignalDetector:
    """Detects whale activity signals across multiple indicators"""

    async def detect_all_signals(self, market_id: str, current_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Run all signal detection methods for a market
        Returns list of detected signals
        """
        signals = []

        # Signal 1: Volume Spike
        volume_signal = await self.detect_volume_spike(market_id, current_data)
        if volume_signal:
            signals.append(volume_signal)

        # Signal 2: Smart Money Accumulation
        smart_money_signal = await self.detect_smart_money(market_id, current_data)
        if smart_money_signal:
            signals.append(smart_money_signal)

        # Signal 3: Order Book Imbalance
        book_imbalance_signal = await self.detect_book_imbalance(current_data)
        if book_imbalance_signal:
            signals.append(book_imbalance_signal)

        # Signal 4: Liquidity Drain
        liquidity_drain_signal = await self.detect_liquidity_drain(market_id, current_data)
        if liquidity_drain_signal:
            signals.append(liquidity_drain_signal)

        # Signal 5: Large Single Orders
        large_order_signal = await self.detect_large_orders(market_id, current_data)
        if large_order_signal:
            signals.append(large_order_signal)

        # Save all detected signals to database
        for signal in signals:
            await db.save_signal(
                market_id=market_id,
                signal_type=signal['type'],
                value=signal['value'],
                threshold=signal['threshold'],
                metadata=json.dumps(signal.get('metadata', {}))
            )

        if signals:
            logger.info(f"Market {market_id}: Detected {len(signals)} signals")

        return signals

    async def detect_volume_spike(self, market_id: str, current_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Signal 1: Volume Spike
        Detects when current 5-min volume is >5x the 1-hour rolling average
        """
        try:
            current_volume = current_data.get('volume', 0)

            # Get snapshots from the last hour
            snapshots = await db.get_recent_snapshots(
                market_id,
                minutes=settings.VOLUME_SPIKE_WINDOW_MINUTES
            )

            if len(snapshots) < 2:
                return None  # Not enough historical data

            # Calculate average volume from historical snapshots
            historical_volumes = [s['volume'] for s in snapshots[1:]]  # Exclude current
            avg_volume = sum(historical_volumes) / len(historical_volumes) if historical_volumes else 0

            if avg_volume == 0:
                return None

            # Calculate volume multiple
            volume_multiple = current_volume / avg_volume

            # Check if spike threshold is met
            if volume_multiple >= settings.VOLUME_SPIKE_MULTIPLIER:
                return {
                    'type': SignalType.VOLUME_SPIKE,
                    'value': volume_multiple,
                    'threshold': settings.VOLUME_SPIKE_MULTIPLIER,
                    'metadata': {
                        'current_volume': current_volume,
                        'avg_volume': avg_volume,
                        'spike_magnitude': f"{volume_multiple:.1f}x"
                    }
                }

            return None

        except Exception as e:
            logger.error(f"Error detecting volume spike for {market_id}: {e}")
            return None

    async def detect_smart_money(self, market_id: str, current_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Signal 2: Smart Money Accumulation
        Detects high volume (>$50k) with minimal price movement (<2%)
        Indicates whales accumulating without moving the market
        """
        try:
            current_volume = current_data.get('volume', 0)
            current_price = current_data.get('yes_price', 0.5)

            # Check volume threshold
            if current_volume < settings.SMART_MONEY_MIN_VOLUME:
                return None

            # Get previous snapshot to calculate price change
            snapshots = await db.get_recent_snapshots(market_id, minutes=10)
            if len(snapshots) < 2:
                return None

            prev_snapshot = snapshots[1]  # Second most recent
            prev_price = prev_snapshot['yes_price']

            # Calculate price change percentage
            price_change_pct = abs((current_price - prev_price) / prev_price * 100) if prev_price > 0 else 0

            # Smart money detected: high volume + low price change
            if price_change_pct <= settings.SMART_MONEY_MAX_PRICE_CHANGE_PCT:
                return {
                    'type': SignalType.SMART_MONEY,
                    'value': current_volume,
                    'threshold': settings.SMART_MONEY_MIN_VOLUME,
                    'metadata': {
                        'volume': current_volume,
                        'price_change_pct': round(price_change_pct, 2),
                        'current_price': current_price,
                        'prev_price': prev_price
                    }
                }

            return None

        except Exception as e:
            logger.error(f"Error detecting smart money for {market_id}: {e}")
            return None

    async def detect_book_imbalance(self, current_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Signal 3: Order Book Imbalance
        Detects when buy/sell orders are heavily skewed (>70/30)
        """
        try:
            buy_volume = current_data.get('total_buy_volume', 0)
            sell_volume = current_data.get('total_sell_volume', 0)
            total_volume = buy_volume + sell_volume

            if total_volume == 0:
                return None

            buy_ratio = buy_volume / total_volume

            # Check if imbalance exceeds threshold (either direction)
            if buy_ratio >= settings.ORDER_BOOK_IMBALANCE_THRESHOLD:
                # Strong buy pressure
                return {
                    'type': SignalType.BOOK_IMBALANCE,
                    'value': buy_ratio,
                    'threshold': settings.ORDER_BOOK_IMBALANCE_THRESHOLD,
                    'metadata': {
                        'direction': Direction.YES,
                        'buy_ratio': round(buy_ratio, 3),
                        'sell_ratio': round(1 - buy_ratio, 3),
                        'imbalance_pct': round(buy_ratio * 100, 1)
                    }
                }
            elif buy_ratio <= (1 - settings.ORDER_BOOK_IMBALANCE_THRESHOLD):
                # Strong sell pressure
                return {
                    'type': SignalType.BOOK_IMBALANCE,
                    'value': 1 - buy_ratio,
                    'threshold': settings.ORDER_BOOK_IMBALANCE_THRESHOLD,
                    'metadata': {
                        'direction': Direction.NO,
                        'buy_ratio': round(buy_ratio, 3),
                        'sell_ratio': round(1 - buy_ratio, 3),
                        'imbalance_pct': round((1 - buy_ratio) * 100, 1)
                    }
                }

            return None

        except Exception as e:
            logger.error(f"Error detecting book imbalance: {e}")
            return None

    async def detect_liquidity_drain(self, market_id: str, current_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Signal 4: Liquidity Drain
        Detects when liquidity drops >20% in 5 minutes
        Indicates market makers pulling liquidity (possible insider info)
        """
        try:
            current_liquidity = current_data.get('liquidity', 0)

            # Get snapshot from 5 minutes ago
            snapshots = await db.get_recent_snapshots(market_id, minutes=10)
            if len(snapshots) < 2:
                return None

            prev_snapshot = snapshots[1]
            prev_liquidity = prev_snapshot['liquidity']

            if prev_liquidity == 0:
                return None

            # Calculate liquidity change
            liquidity_change_pct = ((prev_liquidity - current_liquidity) / prev_liquidity) * 100

            # Check if drain threshold is met
            if liquidity_change_pct >= settings.LIQUIDITY_DRAIN_THRESHOLD_PCT:
                return {
                    'type': SignalType.LIQUIDITY_DRAIN,
                    'value': liquidity_change_pct,
                    'threshold': settings.LIQUIDITY_DRAIN_THRESHOLD_PCT,
                    'metadata': {
                        'current_liquidity': current_liquidity,
                        'prev_liquidity': prev_liquidity,
                        'drain_pct': round(liquidity_change_pct, 1)
                    }
                }

            return None

        except Exception as e:
            logger.error(f"Error detecting liquidity drain for {market_id}: {e}")
            return None

    async def detect_large_orders(self, market_id: str, current_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Signal 5: Large Single Orders
        Detects individual trades >$50k
        Direct whale activity
        """
        try:
            # Fetch recent trades from CLOB API
            trades = await polymarket_client.get_recent_trades(market_id, limit=50)

            if not trades:
                return None

            # Find trades in the last 5 minutes
            five_mins_ago = datetime.utcnow() - timedelta(minutes=5)
            recent_large_trades = []

            for trade in trades:
                trade_time = datetime.fromisoformat(trade.get('timestamp', '').replace('Z', '+00:00'))
                trade_size = float(trade.get('size', 0))
                trade_price = float(trade.get('price', 0))
                trade_value = trade_size * trade_price

                if trade_time >= five_mins_ago and trade_value >= settings.LARGE_ORDER_THRESHOLD:
                    recent_large_trades.append({
                        'size': trade_size,
                        'price': trade_price,
                        'value': trade_value,
                        'side': trade.get('side'),
                        'timestamp': trade.get('timestamp')
                    })

            # If we found large trades, return signal with the largest one
            if recent_large_trades:
                largest_trade = max(recent_large_trades, key=lambda t: t['value'])

                return {
                    'type': SignalType.LARGE_ORDER,
                    'value': largest_trade['value'],
                    'threshold': settings.LARGE_ORDER_THRESHOLD,
                    'metadata': {
                        'trade_value': largest_trade['value'],
                        'trade_size': largest_trade['size'],
                        'trade_price': largest_trade['price'],
                        'side': largest_trade['side'],
                        'total_large_trades': len(recent_large_trades)
                    }
                }

            return None

        except Exception as e:
            logger.error(f"Error detecting large orders for {market_id}: {e}")
            return None

    def determine_direction(self, signals: List[Dict[str, Any]], current_price: float) -> str:
        """
        Determine recommended betting direction based on signals
        """
        if not signals:
            return Direction.NEUTRAL

        # Analyze signal types for directional bias
        buy_signals = 0
        sell_signals = 0

        for signal in signals:
            signal_type = signal['type']
            metadata = signal.get('metadata', {})

            if signal_type == SignalType.VOLUME_SPIKE:
                # Volume spike typically means buy pressure if price is rising
                if current_price > 0.5:
                    buy_signals += 1

            elif signal_type == SignalType.SMART_MONEY:
                # Smart money accumulation = buy signal
                buy_signals += 1

            elif signal_type == SignalType.BOOK_IMBALANCE:
                # Follow the imbalance direction
                direction = metadata.get('direction')
                if direction == Direction.YES:
                    buy_signals += 1
                elif direction == Direction.NO:
                    sell_signals += 1

            elif signal_type == SignalType.LIQUIDITY_DRAIN:
                # Liquidity drain often precedes price movement
                # Slight buy bias as whales may be preparing to buy
                buy_signals += 0.5

            elif signal_type == SignalType.LARGE_ORDER:
                # Follow the side of large order
                side = metadata.get('side', '').lower()
                if 'buy' in side:
                    buy_signals += 1
                elif 'sell' in side:
                    sell_signals += 1

        # Determine overall direction
        if buy_signals > sell_signals:
            return Direction.YES
        elif sell_signals > buy_signals:
            return Direction.NO
        else:
            return Direction.NEUTRAL


# Global detector instance
signal_detector = SignalDetector()
