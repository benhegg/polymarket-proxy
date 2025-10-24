"""
Whale Score Calculator
Calculates 0-100 whale confidence score based on detected signals
"""
import logging
from typing import List, Dict, Any
from config import settings, SignalType

logger = logging.getLogger(__name__)


class WhaleScorer:
    """Calculates whale confidence scores for betting recommendations"""

    def __init__(self):
        # Signal weights (must sum to 100)
        self.weights = {
            SignalType.VOLUME_SPIKE: settings.SCORE_WEIGHT_VOLUME_SPIKE,  # 30
            SignalType.SMART_MONEY: settings.SCORE_WEIGHT_SMART_MONEY,    # 25
            SignalType.BOOK_IMBALANCE: settings.SCORE_WEIGHT_BOOK_IMBALANCE,  # 20
            SignalType.LIQUIDITY_DRAIN: settings.SCORE_WEIGHT_LIQUIDITY_DRAIN,  # 15
            SignalType.LARGE_ORDER: settings.SCORE_WEIGHT_LARGE_ORDER,    # 10
        }

    def calculate_score(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate whale score (0-100) based on detected signals

        Returns:
            {
                'whale_score': int (0-100),
                'confidence': str ('LOW', 'MEDIUM', 'HIGH'),
                'signals_fired': list of signal types,
                'breakdown': dict of scores by signal type
            }
        """
        if not signals:
            return {
                'whale_score': 0,
                'confidence': 'NONE',
                'signals_fired': [],
                'breakdown': {}
            }

        total_score = 0
        breakdown = {}
        signals_fired = []

        for signal in signals:
            signal_type = signal['type']
            base_weight = self.weights.get(signal_type, 0)

            # Calculate intensity multiplier (0.5 to 1.5) based on how far signal exceeded threshold
            multiplier = self._calculate_intensity(signal)

            # Final score for this signal
            signal_score = base_weight * multiplier

            total_score += signal_score
            breakdown[signal_type] = round(signal_score, 1)
            signals_fired.append(signal_type)

        # Cap at 100
        whale_score = min(int(total_score), 100)

        # Determine confidence level
        confidence = self._get_confidence_level(whale_score)

        return {
            'whale_score': whale_score,
            'confidence': confidence,
            'signals_fired': signals_fired,
            'breakdown': breakdown
        }

    def _calculate_intensity(self, signal: Dict[str, Any]) -> float:
        """
        Calculate signal intensity multiplier based on how much threshold was exceeded
        Returns value between 0.5 (barely exceeded) and 1.5 (far exceeded)
        """
        signal_type = signal['type']
        value = signal.get('value', 0)
        threshold = signal.get('threshold', 0)

        if threshold == 0:
            return 1.0

        # Calculate how many times threshold was exceeded
        ratio = value / threshold

        if signal_type == SignalType.VOLUME_SPIKE:
            # Volume spike: 5x = 1.0, 10x = 1.5, 3x = 0.7
            if ratio >= 10:
                return 1.5
            elif ratio >= 7:
                return 1.3
            elif ratio >= 5:
                return 1.0
            else:
                return 0.7

        elif signal_type == SignalType.SMART_MONEY:
            # Smart money: higher volume = higher intensity
            if value >= 200000:  # $200k+
                return 1.5
            elif value >= 100000:  # $100k+
                return 1.3
            elif value >= 50000:  # $50k threshold
                return 1.0
            else:
                return 0.8

        elif signal_type == SignalType.BOOK_IMBALANCE:
            # Book imbalance: higher imbalance = higher intensity
            # 70% = 1.0, 80% = 1.3, 90% = 1.5
            if value >= 0.90:
                return 1.5
            elif value >= 0.80:
                return 1.3
            elif value >= 0.70:
                return 1.0
            else:
                return 0.7

        elif signal_type == SignalType.LIQUIDITY_DRAIN:
            # Liquidity drain: bigger drain = higher intensity
            # 20% = 1.0, 40% = 1.3, 60%+ = 1.5
            if value >= 60:
                return 1.5
            elif value >= 40:
                return 1.3
            elif value >= 20:
                return 1.0
            else:
                return 0.7

        elif signal_type == SignalType.LARGE_ORDER:
            # Large order: bigger trade = higher intensity
            if value >= 200000:  # $200k+
                return 1.5
            elif value >= 100000:  # $100k+
                return 1.3
            elif value >= 50000:  # $50k threshold
                return 1.0
            else:
                return 0.8

        return 1.0  # Default multiplier

    def _get_confidence_level(self, whale_score: int) -> str:
        """Determine confidence level based on whale score"""
        if whale_score >= 75:
            return 'HIGH'
        elif whale_score >= 50:
            return 'MEDIUM'
        elif whale_score >= 25:
            return 'LOW'
        else:
            return 'VERY_LOW'

    def filter_recommendations(self, scored_markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter and rank recommendations
        Returns top N markets above minimum score threshold
        """
        # Filter by minimum score
        filtered = [
            m for m in scored_markets
            if m['whale_score'] >= settings.MIN_WHALE_SCORE
        ]

        # Sort by whale score (descending)
        filtered.sort(key=lambda x: x['whale_score'], reverse=True)

        # Return top N
        return filtered[:settings.MAX_RECOMMENDATIONS]


# Global scorer instance
whale_scorer = WhaleScorer()
