from datetime import datetime

import pandas as pd

from app.agents.outcome_evaluator_agent import OutcomeEvaluatorAgent
from app.agents.prediction_evaluator_agent import PredictionEvaluatorAgent


def _sample_market_data():
    index = pd.date_range(end=datetime(2026, 3, 24), periods=90, freq='D')
    close = pd.Series(range(100, 190), index=index, dtype=float)
    return pd.DataFrame({
        'Close': close,
        'High': close + 2,
        'Low': close - 2,
        'Volume': 100000,
    })


def test_prediction_evaluator_allows_strong_forecast():
    evaluator = PredictionEvaluatorAgent()
    data = _sample_market_data()

    result = evaluator.evaluate_pre_prediction(
        symbol='TEST',
        enriched_data=data,
        data_quality=0.92,
        market_regime='bull',
        prediction=191.0,
        confidence=0.88,
        base_confidence=0.83,
        confidence_adjustment=0.05,
        prediction_interval=(187.0, 194.0),
        uncertainty=1.5,
        model_details=[
            {'prediction': 190.5},
            {'prediction': 191.5},
        ],
    )

    assert result['action'] in {'proceed', 'proceed_with_caution'}
    assert result['score'] >= 0.65
    assert result['summary_metrics']['model_count'] == 2
    assert result['signals']


def test_prediction_evaluator_blocks_invalid_forecast():
    evaluator = PredictionEvaluatorAgent()
    data = _sample_market_data()

    result = evaluator.evaluate_pre_prediction(
        symbol='TEST',
        enriched_data=data,
        data_quality=0.6,
        market_regime='volatile',
        prediction=-10.0,
        confidence=0.4,
        base_confidence=0.35,
        confidence_adjustment=-0.1,
        prediction_interval=(-20.0, 5.0),
        uncertainty=25.0,
        model_details=[
            {'prediction': -10.0},
            {'prediction': 220.0},
        ],
    )

    assert result['action'] == 'block_prediction'
    assert any(flag['code'] == 'NON_POSITIVE_PREDICTION' for flag in result['risk_flags'])


def test_outcome_evaluator_validates_good_realized_result():
    evaluator = OutcomeEvaluatorAgent()

    result = evaluator.evaluate_post_outcome(
        symbol='TEST',
        predicted=191.0,
        actual=192.0,
        prediction_record={
            'last_close': 189.0,
            'prediction_interval': (188.0, 194.0),
            'confidence': 0.84,
        },
    )

    assert result['action'] == 'validated'
    assert result['score'] >= 0.8
    assert result['outcome_metrics']['inside_prediction_interval'] is True


def test_outcome_evaluator_marks_large_miss_for_retraining():
    evaluator = OutcomeEvaluatorAgent()

    result = evaluator.evaluate_post_outcome(
        symbol='TEST',
        predicted=140.0,
        actual=90.0,
        prediction_record={
            'last_close': 100.0,
            'prediction_interval': (130.0, 145.0),
            'confidence': 0.9,
        },
    )

    assert result['action'] == 'retrain_candidate'
    assert any(flag['code'] == 'OVERCONFIDENT_MISS' for flag in result['risk_flags'])

