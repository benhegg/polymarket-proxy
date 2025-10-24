"""
Polymarket API Client
Interacts with Gamma (metadata), CLOB (order book), and Data API (positions)
"""
import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)


class PolymarketClient:
    """Client for all Polymarket APIs"""

    def __init__(self):
        self.gamma_base = settings.POLYMARKET_GAMMA_API
        self.clob_base = settings.POLYMARKET_CLOB_API
        self.data_base = settings.POLYMARKET_DATA_API
        self.timeout = httpx.Timeout(30.0)

    async def get_active_markets(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Fetch active markets from Gamma API
        Filters by minimum volume threshold
        """
        try:
            limit = limit or settings.MARKET_LIMIT
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.gamma_base}/markets",
                    params={
                        "active": "true",
                        "closed": "false",
                        "limit": limit
                    }
                )
                response.raise_for_status()
                markets = response.json()

                # Filter by minimum volume
                filtered = [
                    m for m in markets
                    if float(m.get('volume', 0)) >= settings.MIN_MARKET_VOLUME
                ]

                logger.info(f"Fetched {len(filtered)} markets (volume >= ${settings.MIN_MARKET_VOLUME:,.0f})")
                return filtered

        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []

    async def get_order_book(self, token_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch order book from CLOB API
        Returns bids and asks with prices and sizes
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.clob_base}/book",
                    params={"token_id": token_id}
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error fetching order book for {token_id}: {e}")
            return None

    async def get_recent_trades(self, market_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch recent trades from CLOB API
        Used to detect large orders
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.clob_base}/trades",
                    params={
                        "market": market_id,
                        "limit": limit
                    }
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error fetching trades for {market_id}: {e}")
            return []

    async def get_market_prices(self, token_id: str) -> Optional[Dict[str, float]]:
        """
        Get current bid/ask prices for a token
        """
        try:
            order_book = await self.get_order_book(token_id)
            if not order_book:
                return None

            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])

            return {
                'bid': float(bids[0]['price']) if bids else 0.0,
                'ask': float(asks[0]['price']) if asks else 0.0,
                'mid': (float(bids[0]['price']) + float(asks[0]['price'])) / 2 if bids and asks else 0.0,
                'spread': abs(float(asks[0]['price']) - float(bids[0]['price'])) if bids and asks else 0.0
            }

        except Exception as e:
            logger.error(f"Error getting prices for {token_id}: {e}")
            return None

    async def calculate_order_book_imbalance(self, token_id: str) -> Optional[float]:
        """
        Calculate order book imbalance (buy pressure vs sell pressure)
        Returns ratio: total_buy_volume / (total_buy_volume + total_sell_volume)
        Value of 0.7+ indicates strong buy pressure, <0.3 indicates sell pressure
        """
        try:
            order_book = await self.get_order_book(token_id)
            if not order_book:
                return None

            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])

            # Calculate total volume on each side
            total_bid_volume = sum(float(b['size']) for b in bids)
            total_ask_volume = sum(float(a['size']) for a in asks)

            total_volume = total_bid_volume + total_ask_volume
            if total_volume == 0:
                return 0.5  # Neutral

            buy_ratio = total_bid_volume / total_volume

            return buy_ratio

        except Exception as e:
            logger.error(f"Error calculating imbalance for {token_id}: {e}")
            return None

    async def enrich_market_data(self, market: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich market data with order book and trade information
        This is called during each polling cycle
        """
        try:
            # Parse outcome prices to get YES/NO token IDs
            outcome_prices = market.get('outcomePrices')
            if isinstance(outcome_prices, str):
                import json
                outcome_prices = json.loads(outcome_prices)

            yes_price = float(outcome_prices[0]) if outcome_prices and len(outcome_prices) > 0 else 0.5
            no_price = 1 - yes_price

            # Get market tokens for order book data
            tokens = market.get('tokens', [])
            yes_token_id = tokens[0].get('token_id') if len(tokens) > 0 else None
            no_token_id = tokens[1].get('token_id') if len(tokens) > 1 else None

            enriched = {
                'id': market.get('id'),
                'question': market.get('question'),
                'category': market.get('category'),
                'slug': market.get('slug'),
                'volume': float(market.get('volume', 0)),
                'liquidity': float(market.get('liquidity', 0)),
                'yes_price': yes_price,
                'no_price': no_price,
                'yes_token_id': yes_token_id,
                'no_token_id': no_token_id,
                'timestamp': datetime.utcnow()
            }

            # Fetch order book data for YES token (if available)
            if yes_token_id:
                order_book = await self.get_order_book(yes_token_id)
                if order_book:
                    bids = order_book.get('bids', [])
                    asks = order_book.get('asks', [])

                    enriched['yes_bid'] = float(bids[0]['price']) if bids else None
                    enriched['yes_ask'] = float(asks[0]['price']) if asks else None
                    enriched['buy_orders_count'] = len(bids)
                    enriched['sell_orders_count'] = len(asks)
                    enriched['total_buy_volume'] = sum(float(b['size']) for b in bids)
                    enriched['total_sell_volume'] = sum(float(a['size']) for a in asks)

            # Fetch NO token prices (optional, for completeness)
            if no_token_id:
                no_prices = await self.get_market_prices(no_token_id)
                if no_prices:
                    enriched['no_bid'] = no_prices['bid']
                    enriched['no_ask'] = no_prices['ask']

            return enriched

        except Exception as e:
            logger.error(f"Error enriching market {market.get('id')}: {e}")
            # Return basic data even if enrichment fails
            return {
                'id': market.get('id'),
                'question': market.get('question'),
                'volume': float(market.get('volume', 0)),
                'liquidity': float(market.get('liquidity', 0)),
                'yes_price': 0.5,
                'no_price': 0.5,
                'timestamp': datetime.utcnow()
            }


# Global client instance
polymarket_client = PolymarketClient()
