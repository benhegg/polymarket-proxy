"""
Configuration for Polymarket Whale Tracker
"""
import os
from pydantic import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # API Endpoints
    POLYMARKET_GAMMA_API: str = "https://gamma-api.polymarket.com"
    POLYMARKET_CLOB_API: str = "https://clob.polymarket.com"
    POLYMARKET_DATA_API: str = "https://data-api.polymarket.com"

    # Polling Configuration
    POLL_INTERVAL_SECONDS: int = 300  # 5 minutes

    # Market Filters
    MIN_MARKET_VOLUME: float = 500000.0  # $500k minimum volume
    MARKET_LIMIT: int = 100  # Max markets to track per poll

    # Signal Detection Thresholds
    # 1. Volume Spike: >5x the 1-hour rolling average
    VOLUME_SPIKE_MULTIPLIER: float = 5.0
    VOLUME_SPIKE_WINDOW_MINUTES: int = 60  # 1-hour rolling window

    # 2. Smart Money: >$50k volume with <2% price change
    SMART_MONEY_MIN_VOLUME: float = 50000.0
    SMART_MONEY_MAX_PRICE_CHANGE_PCT: float = 2.0

    # 3. Order Book Imbalance: 70/30 split or worse
    ORDER_BOOK_IMBALANCE_THRESHOLD: float = 0.70

    # 4. Liquidity Drain: >20% decrease in 5 min
    LIQUIDITY_DRAIN_THRESHOLD_PCT: float = 20.0

    # 5. Large Single Orders: >$50k
    LARGE_ORDER_THRESHOLD: float = 50000.0

    # Whale Score Weights (must sum to 100)
    SCORE_WEIGHT_VOLUME_SPIKE: int = 30
    SCORE_WEIGHT_SMART_MONEY: int = 25
    SCORE_WEIGHT_BOOK_IMBALANCE: int = 20
    SCORE_WEIGHT_LIQUIDITY_DRAIN: int = 15
    SCORE_WEIGHT_LARGE_ORDER: int = 10

    # Recommendation Thresholds
    MIN_WHALE_SCORE: int = 50  # Minimum score to show as recommendation
    HIGH_CONFIDENCE_SCORE: int = 75  # Score threshold for Telegram alerts
    MAX_RECOMMENDATIONS: int = 10  # Top N recommendations to display

    # Paper Trading
    PAPER_TRADING_ENABLED: bool = True
    PAPER_TRADE_AMOUNT: float = 100.0  # Default bet size for paper trades
    PAPER_TRADE_AUTO_ENTER: bool = True  # Auto-enter paper trades for signals >75
    PAPER_TRADE_HOLD_HOURS: int = 24  # How long to hold paper trades

    # Database
    DATABASE_PATH: str = "./data/whales.db"
    DATA_RETENTION_DAYS: int = 30

    # API Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_CORS_ORIGINS: list = ["*"]  # Allow all origins (adjust for production)

    # Telegram Notifications
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Signal type constants
class SignalType:
    VOLUME_SPIKE = "volume_spike"
    SMART_MONEY = "smart_money"
    BOOK_IMBALANCE = "book_imbalance"
    LIQUIDITY_DRAIN = "liquidity_drain"
    LARGE_ORDER = "large_order"

    @classmethod
    def all(cls):
        return [
            cls.VOLUME_SPIKE,
            cls.SMART_MONEY,
            cls.BOOK_IMBALANCE,
            cls.LIQUIDITY_DRAIN,
            cls.LARGE_ORDER
        ]


# Recommendation directions
class Direction:
    YES = "YES"
    NO = "NO"
    NEUTRAL = "NEUTRAL"
