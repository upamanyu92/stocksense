"""
Shared helpers for deterministic evaluative agents.
"""
from datetime import datetime
from typing import Any, Dict, List
import logging


class BaseEvaluativeAgent:
    """Base helper class for evaluative agents."""

    def __init__(self, name: str, version: str = "v1"):
        self.name = name
        self.version = version
        self.logger = logging.getLogger(f"Agent.{name}")

    @staticmethod
    def clip_score(value: Any, default: float = 0.0) -> float:
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return default
        return max(0.0, min(1.0, numeric_value))

    @staticmethod
    def score_band(score: float) -> str:
        if score >= 0.8:
            return 'strong'
        if score >= 0.65:
            return 'moderate'
        if score >= 0.5:
            return 'weak'
        return 'poor'

    @staticmethod
    def signal(name: str, value: float, weight: float, reason: str) -> Dict[str, Any]:
        value = max(0.0, min(1.0, float(value)))
        status = 'pass' if value >= 0.75 else 'warn' if value >= 0.5 else 'fail'
        return {
            'name': name,
            'value': value,
            'weight': weight,
            'weighted_contribution': round(value * weight, 4),
            'status': status,
            'reason': reason,
        }

    @staticmethod
    def risk_flag(code: str, severity: str, message: str) -> Dict[str, str]:
        return {
            'code': code,
            'severity': severity,
            'message': message,
        }

    def finalize_score(self, signals: List[Dict[str, Any]]) -> float:
        score = sum(signal['weighted_contribution'] for signal in signals)
        return self.clip_score(score)

    def base_payload(self, phase: str, symbol: str) -> Dict[str, Any]:
        return {
            'phase': phase,
            'symbol': symbol,
            'evaluator': self.name,
            'evaluator_version': self.version,
            'created_at': datetime.now().isoformat(),
        }

