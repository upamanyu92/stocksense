"""
Tests for portfolio management, settings, onboarding, and symbol normalization features.
"""
import io
import json

import pytest


# ---------------------------------------------------------------------------
# Portfolio API Tests
# ---------------------------------------------------------------------------

class TestPortfolioHoldings:
    """Tests for /api/portfolio/holdings endpoints."""

    def test_get_holdings_unauthenticated(self, client):
        resp = client.get('/api/portfolio/holdings')
        assert resp.status_code in (302, 401)

    def test_get_holdings_authenticated(self, logged_in_client):
        resp = logged_in_client.get('/api/portfolio/holdings')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'holdings' in data
        assert 'summary' in data

    def test_add_holding(self, logged_in_client):
        resp = logged_in_client.post(
            '/api/portfolio/holdings',
            json={
                'stock_symbol': 'INFY',
                'company_name': 'Infosys Ltd',
                'quantity': 50,
                'avg_buy_price': 1500.0,
                'current_value': 1550.0,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'holding_id' in data

    def test_add_holding_invalid(self, logged_in_client):
        resp = logged_in_client.post(
            '/api/portfolio/holdings',
            json={'stock_symbol': '', 'quantity': 0, 'avg_buy_price': 0},
        )
        assert resp.status_code == 400

    def test_delete_holding(self, logged_in_client):
        # Add then delete
        resp = logged_in_client.post(
            '/api/portfolio/holdings',
            json={'stock_symbol': 'WIPRO', 'quantity': 10, 'avg_buy_price': 400},
        )
        hid = resp.get_json().get('holding_id')
        if hid:
            resp = logged_in_client.delete(f'/api/portfolio/holdings/{hid}')
            assert resp.status_code == 200

    def test_delete_holding_not_found(self, logged_in_client):
        resp = logged_in_client.delete('/api/portfolio/holdings/99999')
        assert resp.status_code == 404


class TestPortfolioTransactions:
    """Tests for /api/portfolio/transactions endpoints."""

    def test_add_transaction(self, logged_in_client):
        resp = logged_in_client.post(
            '/api/portfolio/transactions',
            json={
                'stock_symbol': 'RELIANCE',
                'transaction_type': 'BUY',
                'quantity': 20,
                'price': 2500.0,
                'transaction_date': '2025-01-15',
                'company_name': 'Reliance Industries',
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'transaction_id' in data

    def test_add_transaction_invalid_type(self, logged_in_client):
        resp = logged_in_client.post(
            '/api/portfolio/transactions',
            json={
                'stock_symbol': 'TCS',
                'transaction_type': 'INVALID',
                'quantity': 10,
                'price': 100,
            },
        )
        assert resp.status_code == 400

    def test_get_transactions(self, logged_in_client):
        # Add a transaction first
        logged_in_client.post(
            '/api/portfolio/transactions',
            json={
                'stock_symbol': 'TCS',
                'transaction_type': 'BUY',
                'quantity': 5,
                'price': 3500,
                'transaction_date': '2025-03-01',
            },
        )
        resp = logged_in_client.get('/api/portfolio/transactions')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert len(data['transactions']) >= 1

    def test_get_transactions_filtered(self, logged_in_client):
        resp = logged_in_client.get('/api/portfolio/transactions?symbol=TCS')
        assert resp.status_code == 200

    def test_delete_transaction(self, logged_in_client):
        # Add then delete
        resp = logged_in_client.post(
            '/api/portfolio/transactions',
            json={
                'stock_symbol': 'HDFC',
                'transaction_type': 'BUY',
                'quantity': 10,
                'price': 1600,
                'transaction_date': '2025-02-01',
            },
        )
        tid = resp.get_json().get('transaction_id')
        if tid:
            resp = logged_in_client.delete(f'/api/portfolio/transactions/{tid}')
            assert resp.status_code == 200


class TestPortfolioAnalytics:
    """Tests for portfolio analytics endpoints."""

    def test_get_summary(self, logged_in_client):
        resp = logged_in_client.get('/api/portfolio/summary')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'summary' in data

    def test_get_allocation(self, logged_in_client):
        resp = logged_in_client.get('/api/portfolio/allocation')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'allocation' in data

    def test_get_gainers_losers(self, logged_in_client):
        resp = logged_in_client.get('/api/portfolio/gainers-losers')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'gainers' in data
        assert 'losers' in data


class TestPortfolioImport:
    """Tests for portfolio import endpoints."""

    def test_import_xlsx_no_file(self, logged_in_client):
        resp = logged_in_client.post('/api/portfolio/import/xlsx')
        assert resp.status_code == 400

    def test_import_csv_no_file(self, logged_in_client):
        resp = logged_in_client.post('/api/portfolio/import/csv')
        assert resp.status_code == 400

    def test_import_csv_with_valid_file(self, logged_in_client):
        csv_content = "symbol,type,quantity,price,date\nTCS,BUY,10,3500,2025-01-01\nINFY,BUY,20,1500,2025-01-02\n"
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'portfolio.csv'),
        }
        resp = logged_in_client.post(
            '/api/portfolio/import/csv',
            data=data,
            content_type='multipart/form-data',
        )
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['success'] is True
        assert result['imported'] == 2

    def test_import_csv_wrong_extension(self, logged_in_client):
        data = {
            'file': (io.BytesIO(b'data'), 'portfolio.txt'),
        }
        resp = logged_in_client.post(
            '/api/portfolio/import/csv',
            data=data,
            content_type='multipart/form-data',
        )
        assert resp.status_code == 400

    def test_import_history(self, logged_in_client):
        resp = logged_in_client.get('/api/portfolio/import/history')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'imports' in data


# ---------------------------------------------------------------------------
# Settings & Onboarding API Tests
# ---------------------------------------------------------------------------

class TestSettings:
    """Tests for /api/settings/ endpoints."""

    def test_get_settings_unauthenticated(self, client):
        resp = client.get('/api/settings/')
        assert resp.status_code in (302, 401)

    def test_get_settings(self, logged_in_client):
        resp = logged_in_client.get('/api/settings/')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'settings' in data
        assert data['settings']['default_exchange'] == 'NSE'

    def test_update_settings(self, logged_in_client):
        resp = logged_in_client.put(
            '/api/settings/',
            json={'theme': 'light', 'risk_tolerance': 'aggressive'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['settings']['theme'] == 'light'
        assert data['settings']['risk_tolerance'] == 'aggressive'

    def test_update_settings_invalid(self, logged_in_client):
        resp = logged_in_client.put(
            '/api/settings/',
            json={'nonexistent_field': 'value'},
        )
        assert resp.status_code == 400


class TestOnboarding:
    """Tests for onboarding flow."""

    def test_get_onboarding_status(self, logged_in_client):
        resp = logged_in_client.get('/api/settings/onboarding')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'completed' in data
        assert 'current_step' in data
        assert 'steps' in data

    def test_advance_onboarding(self, logged_in_client):
        resp = logged_in_client.post(
            '/api/settings/onboarding/advance',
            json={},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['current_step'] in ('model_setup', 'welcome')

    def test_skip_onboarding(self, logged_in_client):
        resp = logged_in_client.post(
            '/api/settings/onboarding/skip',
            json={},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True


class TestModelStatus:
    """Tests for model status endpoint."""

    def test_get_model_status(self, logged_in_client):
        resp = logged_in_client.get('/api/settings/model-status')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'active_model' in data


# ---------------------------------------------------------------------------
# Symbol Normalization Tests
# ---------------------------------------------------------------------------

class TestSymbolUtils:
    """Tests for symbol normalization utilities."""

    def test_normalize_nse(self):
        from app.utils.symbol_utils import normalize_symbol
        assert normalize_symbol('RELIANCE') == 'RELIANCE.NS'
        assert normalize_symbol('RELIANCE.NS') == 'RELIANCE.NS'

    def test_normalize_bse(self):
        from app.utils.symbol_utils import normalize_symbol
        assert normalize_symbol('TCS', 'BSE') == 'TCS.BO'
        assert normalize_symbol('TCS.BO') == 'TCS.BO'

    def test_normalize_us(self):
        from app.utils.symbol_utils import normalize_symbol
        assert normalize_symbol('AAPL', 'NYSE') == 'AAPL'
        assert normalize_symbol('GOOG', 'NASDAQ') == 'GOOG'

    def test_strip_suffix(self):
        from app.utils.symbol_utils import strip_exchange_suffix
        assert strip_exchange_suffix('RELIANCE.NS') == 'RELIANCE'
        assert strip_exchange_suffix('TCS.BO') == 'TCS'
        assert strip_exchange_suffix('AAPL') == 'AAPL'

    def test_get_exchange(self):
        from app.utils.symbol_utils import get_exchange
        assert get_exchange('RELIANCE.NS') == 'NSE'
        assert get_exchange('TCS.BO') == 'BSE'
        assert get_exchange('AAPL') == 'US'

    def test_validate_symbol(self):
        from app.utils.symbol_utils import validate_symbol
        assert validate_symbol('RELIANCE.NS') is True
        assert validate_symbol('TCS') is True
        assert validate_symbol('') is False
        assert validate_symbol('...') is False

    def test_parse_symbol_input(self):
        from app.utils.symbol_utils import parse_symbol_input
        norm, base = parse_symbol_input('NSE:RELIANCE')
        assert norm == 'RELIANCE.NS'
        assert base == 'RELIANCE'

    def test_format_display(self):
        from app.utils.symbol_utils import format_display_symbol
        assert format_display_symbol('RELIANCE.NS') == 'RELIANCE'
        assert format_display_symbol('TCS.BO') == 'TCS'

    def test_infer_exchange(self):
        from app.utils.symbol_utils import infer_exchange_from_symbol
        assert infer_exchange_from_symbol('RELIANCE') == 'NSE'
        assert infer_exchange_from_symbol('500325') == 'BSE'


# ---------------------------------------------------------------------------
# Portfolio Service Unit Tests
# ---------------------------------------------------------------------------

class TestPortfolioService:
    """Tests for PortfolioService business logic."""

    def test_broker_format_detection(self):
        from app.services.portfolio_service import PortfolioService
        assert PortfolioService._detect_broker_format(['tradingsymbol', 'quantity', 'price']) == 'zerodha'
        assert PortfolioService._detect_broker_format(['scrip name', 'quantity', 'price']) == 'groww'
        assert PortfolioService._detect_broker_format(['scheme name', 'units', 'nav']) == 'mutual_fund'
        assert PortfolioService._detect_broker_format(['symbol', 'quantity', 'price']) == 'generic'
        assert PortfolioService._detect_broker_format(['foo', 'bar', 'baz']) == 'unknown'

    def test_parse_date(self):
        from app.services.portfolio_service import PortfolioService
        assert PortfolioService._parse_date('2025-01-15') == '2025-01-15'
        assert PortfolioService._parse_date('15-01-2025') == '2025-01-15'
        assert PortfolioService._parse_date('15/01/2025') == '2025-01-15'
        assert PortfolioService._parse_date('15-Jan-2025') == '2025-01-15'

    def test_parse_row_generic(self):
        from app.services.portfolio_service import PortfolioService
        mapping = {'symbol': 0, 'type': 1, 'quantity': 2, 'price': 3, 'date': 4, 'company': None, 'fees': None}
        row = ('TCS', 'BUY', 10, 3500, '2025-01-01')
        result = PortfolioService._parse_row(row, mapping, 'generic')
        assert result is not None
        assert result['symbol'] == 'TCS'
        assert result['type'] == 'BUY'
        assert result['quantity'] == 10
        assert result['price'] == 3500

    def test_parse_row_sell(self):
        from app.services.portfolio_service import PortfolioService
        mapping = {'symbol': 0, 'type': 1, 'quantity': 2, 'price': 3, 'date': 4, 'company': None, 'fees': None}
        row = ('INFY', 'SELL', 5, 1600, '2025-02-01')
        result = PortfolioService._parse_row(row, mapping, 'generic')
        assert result is not None
        assert result['type'] == 'SELL'

    def test_parse_row_empty(self):
        from app.services.portfolio_service import PortfolioService
        mapping = {'symbol': 0, 'type': 1, 'quantity': 2, 'price': 3, 'date': 4}
        row = ('', '', 0, 0, '')
        result = PortfolioService._parse_row(row, mapping, 'generic')
        assert result is None
