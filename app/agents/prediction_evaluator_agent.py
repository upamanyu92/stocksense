"""
Deterministic pre-prediction evaluator for agentic stock forecasts.
"""
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.agents.base_evaluative_agent import BaseEvaluativeAgent


class PredictionEvaluatorAgent(BaseEvaluativeAgent):
    """Score prediction quality before a forecast is served."""

    def __init__(self, name: str = "PredictionEvaluatorAgent"):
        super().__init__(name)
        self.weights = {
            'model_confidence_score': 0.25,
            'data_quality_score': 0.20,
            'model_agreement_score': 0.20,
            'interval_tightness_score': 0.15,
            'move_plausibility_score': 0.10,
            'regime_stability_score': 0.10,
        }

    def evaluate_pre_prediction(
        self,
        symbol: str,
        enriched_data: Optional[pd.DataFrame],
        data_quality: float,
        market_regime: str,
        prediction: float,
        confidence: float,
        base_confidence: float,
        confidence_adjustment: float,
        prediction_interval: Any,
        uncertainty: float,
        model_details: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        model_details = model_details or []
        last_close = self._get_last_close(enriched_data)
        model_predictions = [
            float(detail['prediction'])
            for detail in model_details
            if isinstance(detail, dict) and detail.get('prediction') is not None
        ]
        agreement_score = self._model_agreement_score(model_predictions, prediction)
        interval_width_pct = self._interval_width_pct(prediction_interval, last_close)
        interval_tightness_score = max(0.0, 1.0 - min(1.0, interval_width_pct / 0.20))
        recent_volatility = self._recent_volatility(enriched_data)
        predicted_move_pct = self._predicted_move_pct(prediction, last_close)
        move_plausibility_score = self._move_plausibility_score(predicted_move_pct, recent_volatility)
        regime_stability_score = {
            'bull': 0.9,
            'bear': 0.85,
            'sideways': 0.8,
            'volatile': 0.55,
        }.get((market_regime or 'sideways').lower(), 0.75)

        signals = [
            self.signal(
                'model_confidence_score',
                self.clip_score(confidence),
                self.weights['model_confidence_score'],
                'Adjusted ensemble confidence after adaptive weighting.',
            ),
            self.signal(
                'data_quality_score',
                self.clip_score(data_quality),
                self.weights['data_quality_score'],
                'Quality of the enriched feature set used for the forecast.',
            ),
            self.signal(
                'model_agreement_score',
                agreement_score,
                self.weights['model_agreement_score'],
                'Agreement across sub-model predictions and ensemble output.',
            ),
            self.signal(
                'interval_tightness_score',
                interval_tightness_score,
                self.weights['interval_tightness_score'],
                'Tighter prediction intervals imply a more stable forecast.',
            ),
            self.signal(
                'move_plausibility_score',
                move_plausibility_score,
                self.weights['move_plausibility_score'],
                'Predicted move is compared with recent realized volatility.',
            ),
            self.signal(
                'regime_stability_score',
                regime_stability_score,
                self.weights['regime_stability_score'],
                'Current market regime influences how aggressively to serve the forecast.',
            ),
        ]
        score = self.finalize_score(signals)
        risk_flags = self._build_risk_flags(
            prediction=prediction,
            confidence_adjustment=confidence_adjustment,
            agreement_score=agreement_score,
            interval_tightness_score=interval_tightness_score,
            predicted_move_pct=predicted_move_pct,
            recent_volatility=recent_volatility,
            market_regime=market_regime,
            enriched_data=enriched_data,
        )
        action = self._derive_action(score, risk_flags)
        payload = self.base_payload('pre_prediction', symbol)
        payload.update({
            'score': score,
            'score_pct': int(round(score * 100)),
            'band': self.score_band(score),
            'verdict': 'approved' if action == 'proceed' else 'review' if action != 'block_prediction' else 'blocked',
            'action': action,
            'signals': signals,
            'risk_flags': risk_flags,
            'summary_metrics': {
                'predicted_price': float(prediction),
                'last_close': last_close,
                'predicted_move_pct': predicted_move_pct,
                'uncertainty': float(uncertainty),
                'interval_width_pct': interval_width_pct,
                'data_quality': self.clip_score(data_quality),
                'base_confidence': self.clip_score(base_confidence),
                'final_confidence': self.clip_score(confidence),
                'market_regime': market_regime,
                'model_count': len(model_details),
            },
            'logic_breakdown': [
                f"Evaluation score {score:.2f} built from confidence, data quality, agreement, interval tightness, move plausibility, and regime stability.",
                f"Serving action set to {action} based on score band and triggered risk flags.",
            ],
            'source_verification': {
                'latest_observation_ts': self._latest_observation_ts(enriched_data),
                'row_count': int(len(enriched_data)) if isinstance(enriched_data, pd.DataFrame) else 0,
                'missing_ratio_required': self._missing_ratio(enriched_data),
            },
        })
        return payload

    def _derive_action(self, score: float, risk_flags: List[Dict[str, str]]) -> str:
        high_flags = {flag['code'] for flag in risk_flags if flag['severity'] == 'high'}
        block_codes = {'NON_POSITIVE_PREDICTION', 'INVALID_NUMERIC_OUTPUT'}
        if high_flags & block_codes or score < 0.5:
            return 'block_prediction'
        if high_flags:
            return 'shadow_only'
        if score >= 0.8:
            return 'proceed'
        if score >= 0.65:
            return 'proceed_with_caution'
        return 'shadow_only'

    def _build_risk_flags(
        self,
        prediction: float,
        confidence_adjustment: float,
        agreement_score: float,
        interval_tightness_score: float,
        predicted_move_pct: Optional[float],
        recent_volatility: Optional[float],
        market_regime: str,
        enriched_data: Optional[pd.DataFrame],
    ) -> List[Dict[str, str]]:
        flags: List[Dict[str, str]] = []
        if not np.isfinite(prediction):
            flags.append(self.risk_flag('INVALID_NUMERIC_OUTPUT', 'high', 'Prediction contains NaN or infinite values.'))
        if prediction <= 0:
            flags.append(self.risk_flag('NON_POSITIVE_PREDICTION', 'high', 'Predicted price must be positive.'))
        if agreement_score < 0.45:
            flags.append(self.risk_flag('LOW_MODEL_AGREEMENT', 'high', 'Sub-model predictions disagree materially.'))
        if interval_tightness_score < 0.35:
            flags.append(self.risk_flag('WIDE_PREDICTION_INTERVAL', 'high', 'Prediction interval is too wide relative to the latest close.'))
        if predicted_move_pct is not None:
            volatility_floor = max(recent_volatility or 0.0, 0.03)
            if predicted_move_pct > max(0.12, volatility_floor * 4):
                flags.append(self.risk_flag('EXTREME_PREDICTED_MOVE', 'high', 'Predicted move is large versus recent realized volatility.'))
        if isinstance(enriched_data, pd.DataFrame) and len(enriched_data) < 60:
            flags.append(self.risk_flag('INSUFFICIENT_HISTORY', 'medium', 'Forecast was made with limited recent history.'))
        if (market_regime or '').lower() == 'volatile':
            flags.append(self.risk_flag('VOLATILE_REGIME', 'medium', 'Adaptive agent detected a volatile market regime.'))
        if confidence_adjustment < 0:
            flags.append(self.risk_flag('NEGATIVE_CONFIDENCE_ADJUSTMENT', 'low', 'Adaptive learning reduced confidence for this setup.'))
        return flags

    @staticmethod
    def _get_last_close(enriched_data: Optional[pd.DataFrame]) -> Optional[float]:
        if isinstance(enriched_data, pd.DataFrame) and not enriched_data.empty and 'Close' in enriched_data.columns:
            return float(enriched_data['Close'].iloc[-1])
        return None

    @staticmethod
    def _recent_volatility(enriched_data: Optional[pd.DataFrame]) -> Optional[float]:
        if not isinstance(enriched_data, pd.DataFrame) or enriched_data.empty or 'Close' not in enriched_data.columns:
            return None
        returns = enriched_data['Close'].pct_change().dropna().tail(20)
        if returns.empty:
            return None
        return float(returns.std())

    @staticmethod
    def _predicted_move_pct(prediction: float, last_close: Optional[float]) -> Optional[float]:
        if last_close in (None, 0):
            return None
        return float(abs(prediction - last_close) / abs(last_close))

    @staticmethod
    def _model_agreement_score(model_predictions: List[float], fallback_prediction: float) -> float:
        predictions = model_predictions or [fallback_prediction]
        if len(predictions) < 2:
            return 1.0
        mean_prediction = abs(float(np.mean(predictions))) or 1e-6
        dispersion = float(np.std(predictions) / mean_prediction)
        return max(0.0, 1.0 - min(1.0, dispersion))

    @staticmethod
    def _interval_width_pct(prediction_interval: Any, last_close: Optional[float]) -> float:
        if not prediction_interval or last_close in (None, 0):
            return 1.0
        try:
            lower, upper = prediction_interval
            return float(abs(upper - lower) / abs(last_close))
        except (TypeError, ValueError):
            return 1.0

    @staticmethod
    def _move_plausibility_score(predicted_move_pct: Optional[float], recent_volatility: Optional[float]) -> float:
        if predicted_move_pct is None:
            return 0.75
        threshold = max(recent_volatility or 0.0, 0.03) * 3
        threshold = max(threshold, 0.05)
        if predicted_move_pct <= threshold:
            return 1.0
        excess = (predicted_move_pct - threshold) / threshold
        return max(0.0, 1.0 - min(1.0, excess))

    @staticmethod
    def _latest_observation_ts(enriched_data: Optional[pd.DataFrame]) -> Optional[str]:
        if not isinstance(enriched_data, pd.DataFrame) or enriched_data.empty:
            return None
        last_index = enriched_data.index[-1]
        if hasattr(last_index, 'isoformat'):
            return last_index.isoformat()
        return str(last_index)

    @staticmethod
    def _missing_ratio(enriched_data: Optional[pd.DataFrame]) -> float:
        if not isinstance(enriched_data, pd.DataFrame) or enriched_data.empty:
            return 1.0
        required_columns = [column for column in ['Close', 'High', 'Low', 'Volume'] if column in enriched_data.columns]
        if not required_columns:
            return 1.0
        return round(float(enriched_data[required_columns].isna().mean().mean()), 4)

