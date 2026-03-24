from datetime import datetime

import pandas as pd

from app.agents.outcome_evaluator_agent import OutcomeEvaluatorAgent
from app.agents.prediction_coordinator import PredictionCoordinator
from app.agents.prediction_evaluator_agent import PredictionEvaluatorAgent


class StubDataAgent:
    name = 'StubDataAgent'

    def __init__(self):
        self.metadata = {'predictions_made': 0}

    def predict(self, symbol, data=None):
        index = pd.date_range(end=datetime(2026, 3, 24), periods=120, freq='D')
        close = pd.Series(range(100, 220), index=index, dtype=float)
        return {
            'enriched_data': pd.DataFrame({
                'Close': close,
                'High': close + 2,
                'Low': close - 2,
                'Volume': 100000,
            }),
            'quality_score': 0.9,
        }

    def get_accuracy(self):
        return 0.0


class StubAdaptiveAgent:
    name = 'StubAdaptiveAgent'

    def __init__(self):
        self.metadata = {'predictions_made': 0}
        self.saved = False

    def load_learning_state(self):
        return None

    def predict(self, symbol, data=None):
        return {
            'market_regime': 'bull',
            'adaptive_weights': {'transformer': 0.6, 'lstm': 0.4},
            'confidence_adjustment': 0.05,
        }

    def learn_from_error(self, model_type, predicted, actual):
        return None

    def update_strategy_performance(self, regime, predicted, actual):
        return None

    def save_learning_state(self):
        self.saved = True

    def get_accuracy(self):
        return 0.0

    def get_learning_report(self):
        return {'model_performance': {}}


class StubEnsembleAgent:
    name = 'StubEnsembleAgent'

    def __init__(self):
        self.metadata = {'predictions_made': 0}
        self.model_weights = {}

    def predict(self, symbol, data=None):
        return {
            'prediction': 223.0,
            'confidence': 0.82,
            'prediction_interval': (220.0, 226.0),
            'uncertainty': 1.2,
            'model_details': [
                {'model_type': 'a', 'prediction': 222.0},
                {'model_type': 'b', 'prediction': 224.0},
            ],
        }

    def update_performance(self, actual, predicted):
        self.metadata['predictions_made'] += 1

    def get_accuracy(self):
        return 1.0


def test_prediction_coordinator_returns_evaluation_and_tracks_outcomes():
    coordinator = PredictionCoordinator(
        min_confidence=0.6,
        data_agent=StubDataAgent(),
        ensemble_agent=StubEnsembleAgent(),
        adaptive_agent=StubAdaptiveAgent(),
        prediction_evaluator=PredictionEvaluatorAgent(),
        outcome_evaluator=OutcomeEvaluatorAgent(),
    )

    result = coordinator.predict('TEST', validate=True)

    assert result['evaluation']['phase'] == 'pre_prediction'
    assert result['serving_action'] in {'proceed', 'proceed_with_caution', 'shadow_only'}
    assert 'PredictionEvaluatorAgent' in result['agents_used']
    assert coordinator.decision_history[-1]['evaluation']['phase'] == 'pre_prediction'

    outcome = coordinator.update_with_actual('TEST', predicted=result['prediction'], actual=224.0)

    assert outcome['phase'] == 'post_outcome'
    assert coordinator.decision_history[-1]['outcome_evaluation']['phase'] == 'post_outcome'

    report = coordinator.get_performance_report()
    assert report['agent_performance']['prediction_evaluator_agent']['evaluations_completed'] == 1
    assert report['agent_performance']['outcome_evaluator_agent']['evaluations_completed'] == 1
    assert report['metrics']['average_evaluation_score'] > 0
    assert report['metrics']['average_outcome_score'] > 0

