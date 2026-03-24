from flask import Flask

from app.api import agentic_routes
from app.api.agentic_routes import agentic_api


class StubCoordinator:
    def __init__(self):
        self.min_confidence = 0.6
        self.updated_threshold = None

    def set_confidence_threshold(self, threshold):
        self.updated_threshold = threshold
        self.min_confidence = threshold

    def predict(self, symbol, validate=True):
        return {
            'symbol': symbol,
            'prediction': 123.45,
            'confidence': 0.81,
            'decision': 'accept',
            'serving_action': 'proceed',
            'evaluation': {
                'phase': 'pre_prediction',
                'action': 'proceed',
                'score': 0.81,
                'score_pct': 81,
            },
        }

    def update_with_actual(self, symbol, predicted, actual):
        return {
            'phase': 'post_outcome',
            'action': 'monitor',
            'score': 0.66,
            'score_pct': 66,
            'symbol': symbol,
        }

    def get_performance_report(self):
        return {
            'metrics': {
                'total_predictions': 3,
                'average_confidence': 0.74,
                'average_evaluation_score': 0.7,
                'blocked_predictions': 1,
            }
        }


def test_agentic_predict_route_returns_evaluation(monkeypatch):
    stub = StubCoordinator()
    monkeypatch.setattr(agentic_routes, 'get_coordinator', lambda: stub)

    app = Flask(__name__)
    app.register_blueprint(agentic_api)
    client = app.test_client()

    response = client.get('/api/agentic/predict/TEST?min_confidence=0.7')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['evaluation']['action'] == 'proceed'
    assert stub.updated_threshold == 0.7


def test_agentic_feedback_route_returns_outcome_evaluation(monkeypatch):
    monkeypatch.setattr(agentic_routes, 'get_coordinator', lambda: StubCoordinator())

    app = Flask(__name__)
    app.register_blueprint(agentic_api)
    client = app.test_client()

    response = client.post('/api/agentic/feedback', json={
        'symbol': 'TEST',
        'predicted': 123.45,
        'actual': 125.00,
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['data']['phase'] == 'post_outcome'
    assert payload['data']['action'] == 'monitor'


def test_agentic_health_route_exposes_evaluator_metrics(monkeypatch):
    monkeypatch.setattr(agentic_routes, 'get_coordinator', lambda: StubCoordinator())

    app = Flask(__name__)
    app.register_blueprint(agentic_api)
    client = app.test_client()

    response = client.get('/api/agentic/health')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['metrics']['average_evaluation_score'] == 0.7
    assert payload['metrics']['blocked_predictions'] == 1

