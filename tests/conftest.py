import sqlite3
from pathlib import Path

import pytest
from flask import Flask
from flask_login import LoginManager, UserMixin

from app.api.auth_routes import auth_bp
from app.api.dashboard_routes import dashboard_bp
from app.api.portfolio_routes import portfolio_bp
from app.api.premium_dashboard_routes import premium_dashboard_bp
from app.api.settings_routes import settings_bp
from app.api.system_routes import system_bp


class DummyUser(UserMixin):
    def __init__(self, user_id: int, username: str, email: str, active: bool = True):
        self.id = user_id
        self.username = username
        self.email = email
        self._active = active

    @property
    def is_active(self):
        return self._active


def _init_test_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS portfolio_holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stock_symbol TEXT NOT NULL,
            company_name TEXT,
            quantity REAL DEFAULT 0,
            avg_buy_price REAL DEFAULT 0,
            current_value REAL DEFAULT 0,
            invested_value REAL DEFAULT 0,
            pnl REAL DEFAULT 0,
            pnl_percent REAL DEFAULT 0,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS watchlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stock_symbol TEXT NOT NULL,
            company_name TEXT,
            display_order INTEGER DEFAULT 0,
            added_at TEXT
        );

        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stock_symbol TEXT NOT NULL,
            predicted_price REAL,
            prediction_date TEXT,
            model_used TEXT
        );

        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stock_symbol TEXT NOT NULL,
            company_name TEXT,
            trade_type TEXT,
            quantity REAL,
            price REAL,
            total_value REAL,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS stock_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            security_id TEXT UNIQUE,
            current_value REAL,
            change REAL,
            p_change REAL,
            market_cap_full TEXT,
            industry TEXT
        );

        CREATE TABLE IF NOT EXISTS user_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            level_name TEXT,
            xp_points INTEGER,
            predictions_made INTEGER,
            successful_predictions INTEGER,
            streak_days INTEGER,
            badges TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS ai_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_symbol TEXT,
            insight_type TEXT,
            message TEXT,
            confidence REAL,
            source TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stock_symbol TEXT,
            alert_type TEXT,
            message TEXT,
            is_triggered INTEGER,
            triggered_at TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS portfolio_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stock_symbol TEXT NOT NULL,
            company_name TEXT,
            transaction_type TEXT NOT NULL,
            quantity REAL NOT NULL DEFAULT 0,
            price REAL NOT NULL DEFAULT 0.0,
            total_value REAL NOT NULL DEFAULT 0.0,
            fees REAL DEFAULT 0.0,
            notes TEXT,
            transaction_date TEXT NOT NULL,
            source TEXT DEFAULT 'manual',
            import_batch_id TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS portfolio_imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            batch_id TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL DEFAULT 'xlsx',
            broker_format TEXT,
            total_rows INTEGER DEFAULT 0,
            imported_rows INTEGER DEFAULT 0,
            skipped_rows INTEGER DEFAULT 0,
            error_rows INTEGER DEFAULT 0,
            errors TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS quote_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            close_price REAL,
            volume INTEGER,
            adj_close REAL,
            source TEXT DEFAULT 'yfinance',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(stock_symbol, date)
        );

        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            default_exchange TEXT DEFAULT 'NSE',
            currency TEXT DEFAULT 'INR',
            theme TEXT DEFAULT 'dark',
            onboarding_completed INTEGER DEFAULT 0,
            onboarding_step TEXT DEFAULT 'welcome',
            default_llm TEXT DEFAULT 'ollama',
            notifications_enabled INTEGER DEFAULT 1,
            email_digest_enabled INTEGER DEFAULT 0,
            risk_tolerance TEXT DEFAULT 'moderate',
            investment_horizon TEXT DEFAULT 'medium',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS portfolio_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            analysis_type TEXT NOT NULL,
            content TEXT NOT NULL,
            model_used TEXT,
            confidence REAL DEFAULT 0.0,
            metadata TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT
        );
        """
    )

    cur.execute(
        """
        INSERT INTO portfolio_holdings
            (user_id, stock_symbol, company_name, quantity, avg_buy_price, current_value, invested_value, pnl, pnl_percent)
        VALUES
            (1, 'TCS', 'Tata Consultancy Services', 10, 3500, 3600, 35000, 1000, 2.86)
        """
    )
    cur.execute(
        """
        INSERT INTO watchlists (user_id, stock_symbol, company_name)
        VALUES (1, 'TCS', 'Tata Consultancy Services')
        """
    )
    cur.execute(
        """
        INSERT INTO predictions (user_id, stock_symbol, predicted_price, prediction_date, model_used)
        VALUES (1, 'TCS', 3800, datetime('now'), 'test-model')
        """
    )
    cur.execute(
        """
        INSERT INTO trades
            (user_id, stock_symbol, company_name, trade_type, quantity, price, total_value, created_at)
        VALUES
            (1, 'TCS', 'Tata Consultancy Services', 'BUY', 10, 3500, 35000, datetime('now'))
        """
    )
    cur.execute(
        """
        INSERT INTO stock_quotes
            (company_name, security_id, current_value, change, p_change, market_cap_full, industry)
        VALUES
            ('Tata Consultancy Services', 'TCS', 3600, 25, 0.7, '1000000', 'IT Services')
        """
    )
    cur.execute(
        """
        INSERT INTO user_levels
            (user_id, level_name, xp_points, predictions_made, successful_predictions, streak_days, badges)
        VALUES
            (1, 'Smart Investor', 120, 5, 3, 2, '[]')
        """
    )
    cur.execute(
        """
        INSERT INTO ai_insights (stock_symbol, insight_type, message, confidence, source, created_at)
        VALUES ('TCS', 'buy_signal', 'TCS likely to rise 3% in next 2 days', 0.82, 'Test AI', datetime('now'))
        """
    )
    cur.execute(
        """
        INSERT INTO alerts (user_id, stock_symbol, alert_type, message, is_triggered, created_at)
        VALUES (1, 'TCS', 'price_alert', 'TCS crossed your target', 1, datetime('now'))
        """
    )

    conn.commit()
    conn.close()


@pytest.fixture()
def app(monkeypatch, tmp_path):
    db_path = tmp_path / "test_stocksense.db"
    _init_test_db(db_path)

    def _get_conn():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr("app.utils.util.get_db_connection", _get_conn)
    monkeypatch.setattr("app.api.premium_dashboard_routes.get_db_connection", _get_conn)

    # Patch session manager for new services
    from app.db import session_manager as sm_module

    class _FakeSessionManager:
        """Minimal session manager backed by the test DB."""
        def _conn(self):
            return _get_conn()

        def fetch_one(self, query, args=()):
            conn = self._conn()
            cur = conn.cursor()
            cur.execute(query, args)
            row = cur.fetchone()
            conn.close()
            return dict(row) if row else None

        def fetch_all(self, query, args=()):
            conn = self._conn()
            cur = conn.cursor()
            cur.execute(query, args)
            rows = cur.fetchall()
            conn.close()
            return [dict(r) for r in rows]

        def insert(self, query, args=()):
            conn = self._conn()
            cur = conn.cursor()
            cur.execute(query, args)
            conn.commit()
            lid = cur.lastrowid
            conn.close()
            return lid

        def update(self, query, args=()):
            conn = self._conn()
            cur = conn.cursor()
            cur.execute(query, args)
            affected = cur.rowcount
            conn.commit()
            conn.close()
            return affected > 0

        def delete(self, query, args=()):
            conn = self._conn()
            cur = conn.cursor()
            cur.execute(query, args)
            affected = cur.rowcount
            conn.commit()
            conn.close()
            return affected > 0

        def execute(self, query, args=(), commit=False, fetch=None):
            conn = self._conn()
            cur = conn.cursor()
            cur.execute(query, args)
            if commit:
                conn.commit()
            result = None
            if fetch == 'one':
                result = cur.fetchone()
            elif fetch == 'all':
                result = cur.fetchall()
            conn.close()
            return result

    _fake_sm = _FakeSessionManager()
    monkeypatch.setattr(sm_module, "get_session_manager", lambda: _fake_sm)

    # Also patch the imported references in service modules
    monkeypatch.setattr("app.services.portfolio_service.get_session_manager", lambda: _fake_sm)
    monkeypatch.setattr("app.services.user_settings_service.get_session_manager", lambda: _fake_sm)
    monkeypatch.setattr("app.services.portfolio_analysis_service.get_session_manager", lambda: _fake_sm)

    users = {
        "demo": DummyUser(1, "demo", "demo@example.com", True),
    }

    from app.services.auth_service import User

    monkeypatch.setattr(User, "verify_password", staticmethod(lambda username, password: username == "demo" and password == "password"))
    monkeypatch.setattr(User, "get_by_username", staticmethod(lambda username: users.get(username)))
    monkeypatch.setattr(User, "get_by_id", staticmethod(lambda user_id: users.get("demo") if int(user_id) == 1 else None))
    monkeypatch.setattr(User, "create_user", staticmethod(lambda username, password, email=None: users.setdefault(username, DummyUser(2, username, email or f"{username}@example.com", True))))

    flask_app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parents[1] / "app" / "templates"),
    )
    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
    )

    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(dashboard_bp)
    flask_app.register_blueprint(premium_dashboard_bp)
    flask_app.register_blueprint(portfolio_bp)
    flask_app.register_blueprint(settings_bp)
    flask_app.register_blueprint(system_bp)

    @flask_app.route("/health")
    def health():
        return {"status": "ok"}, 200

    login_manager = LoginManager()
    login_manager.init_app(flask_app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id: str):
        return users.get("demo") if user_id == "1" else None

    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def logged_in_client(client):
    response = client.post(
        "/login",
        data={"username": "demo", "password": "password"},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    return client

