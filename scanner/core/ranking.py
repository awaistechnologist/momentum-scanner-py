"""Ranking and scoring system for signals."""

import logging
from typing import List, Optional
from scanner.core.models import Signal

logger = logging.getLogger(__name__)


class SignalRanker:
    """Rank and filter signals."""

    @staticmethod
    def rank_signals(signals: List[Signal], top_n: Optional[int] = None) -> List[Signal]:
        """
        Rank signals by score.

        Args:
            signals: List of signals to rank
            top_n: Return only top N signals (None = all)

        Returns:
            Sorted list of signals (highest score first)
        """
        # Sort by score descending
        ranked = sorted(signals, key=lambda s: s.score, reverse=True)

        if top_n:
            return ranked[:top_n]
        return ranked

    @staticmethod
    def filter_by_score(signals: List[Signal], min_score: float) -> List[Signal]:
        """
        Filter signals by minimum score.

        Args:
            signals: List of signals
            min_score: Minimum score threshold

        Returns:
            Filtered list of signals
        """
        return [s for s in signals if s.score >= min_score]

    @staticmethod
    def filter_by_risk_reward(signals: List[Signal], min_rr: float = 1.5) -> List[Signal]:
        """
        Filter signals by minimum risk/reward ratio.

        Args:
            signals: List of signals
            min_rr: Minimum risk/reward ratio

        Returns:
            Filtered list of signals
        """
        return [s for s in signals if s.risk_reward and s.risk_reward >= min_rr]

    @staticmethod
    def get_summary_stats(signals: List[Signal]) -> dict:
        """
        Get summary statistics for a list of signals.

        Args:
            signals: List of signals

        Returns:
            Dictionary with summary stats
        """
        if not signals:
            return {
                "count": 0,
                "avg_score": 0,
                "max_score": 0,
                "min_score": 0,
                "avg_rr": 0
            }

        scores = [s.score for s in signals]
        rrs = [s.risk_reward for s in signals if s.risk_reward]

        return {
            "count": len(signals),
            "avg_score": sum(scores) / len(scores),
            "max_score": max(scores),
            "min_score": min(scores),
            "avg_rr": sum(rrs) / len(rrs) if rrs else 0
        }
