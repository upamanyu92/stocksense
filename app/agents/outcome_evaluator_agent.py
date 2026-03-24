"""
Deterministic post-outcome evaluator for agentic stock forecasts.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.base_evaluative_agent import BaseEvaluativeAgent


class OutcomeEvaluatorAgent(BaseEvaluativeAgent):
    """Score realized prediction quality after actual prices arrive."""

    def __init__(self, name: str = "OutcomeEvaluatorAgent"):
        super().__init__(name)
        self.weights = {
            'absolute_error_score': 0.4,
            'direction_accuracy_score': 0.2,
            'interval_coverage_score': 0.2,
            'confidence_calibration_score': 0.2,
        }

    def evaluate_post_outcome(
        self,
        symbol: str,
        predicted: float,
        actual: float,
        prediction_record: Optional[Dict[str, Any]] = None,
        actual_timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        prediction_record = prediction_record or {}
        last_close = prediction_record.get('last_close')
        prediction_interval = prediction_record.get('prediction_interval')
        predicted_confidence = self.clip_score(prediction_record.get('confidence', 0.5), default=0.5)
        absolute_pct_error = abs(actual - predicted) / abs(actual) if actual else 1.0
        absolute_error_score = max(0.0, 1.0 - min(1.0, absolute_pct_error / 0.10))
        direction_accuracy_score = self._direction_accuracy_score(last_close, predicted, actual)
        interval_coverage_score = self._interval_coverage_score(prediction_interval, actual)
        realized_quality_proxy = max(0.0, 1.0 - min(1.0, absolute_pct_error / 0.10))
        confidence_calibration_score = max(0.0, 1.0 - abs(predicted_confidence - realized_quality_proxy))

        signals = [
            self.signal(
                'absolute_error_score',
                absolute_error_score,
                self.weights['absolute_error_score'],
                'Absolute percentage error against the realized market price.',
            ),
            self.signal(
                'direction_accuracy_score',
                direction_accuracy_score,
                self.weights['direction_accuracy_score'],
                'Whether the predicted move direction matched the actual move.',
            ),
            self.signal(
                'interval_coverage_score',
                interval_coverage_score,
                self.weights['interval_coverage_score'],
                'Whether the realized price landed inside the predicted interval.',
            ),
            self.signal(
                'confidence_calibration_score',
                confidence_calibration_score,
                self.weights['confidence_calibration_score'],
                'Gap between predicted confidence and realized accuracy proxy.',
            ),
        ]
        score = self.finalize_score(signals)
        risk_flags = self._build_risk_flags(
            absolute_pct_error=absolute_pct_error,
            direction_accuracy_score=direction_accuracy_score,
            interval_coverage_score=interval_coverage_score,
            predicted_confidence=predicted_confidence,
        )
        action = self._derive_action(score, risk_flags)
        payload = self.base_payload('post_outcome', symbol)
        payload.update({
            'score': score,
            'score_pct': int(round(score * 100)),
            'band': self.score_band(score),
            'verdict': 'validated' if action == 'validated' else 'review' if action != 'retrain_candidate' else 'failed',
            'action': action,
            'signals': signals,
            'risk_flags': risk_flags,
            'outcome_metrics': {
                'predicted_price': float(predicted),
                'actual_price': float(actual),
                'last_close_at_prediction': last_close,
                'absolute_error': float(abs(actual - predicted)),
                'absolute_pct_error': float(absolute_pct_error),
                'direction_correct': bool(direction_accuracy_score == 1.0),
                'inside_prediction_interval': bool(interval_coverage_score == 1.0),
                'predicted_confidence': predicted_confidence,
                'realized_quality_proxy': float(realized_quality_proxy),
                'calibration_gap': float(abs(predicted_confidence - realized_quality_proxy)),
                'actual_timestamp': actual_timestamp or datetime.now().isoformat(),
            },
            'logic_breakdown': [
                f"Outcome score {score:.2f} built from realized error, move direction, interval coverage, and confidence calibration.",
                f"Post-outcome action set to {action} based on realized quality and evaluator risk flags.",
            ],
        })
        return payload

    def _derive_action(self, score: float, risk_flags: List[Dict[str, str]]) -> str:
        high_flag_count = len([flag for flag in risk_flags if flag['severity'] == 'high'])
        if high_flag_count >= 2 or score < 0.4:
            return 'retrain_candidate'
        if score >= 0.8 and high_flag_count == 0:
            return 'validated'
        if score >= 0.6:
            return 'monitor'
        return 'recalibrate'

    def _build_risk_flags(
        self,
        absolute_pct_error: float,
        direction_accuracy_score: float,
        interval_coverage_score: float,
        predicted_confidence: float,
    ) -> List[Dict[str, str]]:
        flags: List[Dict[str, str]] = []
        if absolute_pct_error > 0.10:
            flags.append(self.risk_flag('LARGE_ABSOLUTE_ERROR', 'high', 'Absolute percentage error exceeded the acceptable band.'))
        if predicted_confidence >= 0.75 and absolute_pct_error > 0.08:
            flags.append(self.risk_flag('OVERCONFIDENT_MISS', 'high', 'High-confidence forecast missed by too much.'))
        if direction_accuracy_score == 0.0:
            flags.append(self.risk_flag('MISSED_DIRECTION', 'medium', 'Predicted price moved in the wrong direction from the latest close.'))
        if interval_coverage_score == 0.0:
            flags.append(self.risk_flag('OUTSIDE_PREDICTION_INTERVAL', 'medium', 'Realized price fell outside the predicted interval.'))
        return flags

    @staticmethod
    def _direction_accuracy_score(last_close: Optional[float], predicted: float, actual: float) -> float:
        if last_close in (None, 0):
            return 0.5
        predicted_direction = predicted - last_close
        actual_direction = actual - last_close
        if predicted_direction == 0 or actual_direction == 0:
            return 0.5
        return 1.0 if (predicted_direction > 0) == (actual_direction > 0) else 0.0

    @staticmethod
    def _interval_coverage_score(prediction_interval: Any, actual: float) -> float:
        if not prediction_interval:
            return 0.5
        try:
            lower, upper = prediction_interval
        except (TypeError, ValueError):
            return 0.5
        return 1.0 if lower <= actual <= upper else 0.0

