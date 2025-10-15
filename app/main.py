# Main Flask application entry point
import logging
import os

from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager

from app.routes.auth_routes import auth_bp
from app.routes.watchlist_routes import watchlist_bp
from app.routes.stock_routes import stock_bp
from app.routes.prediction_routes import prediction_bp
from app.routes.system_routes import system_bp
from app.routes.agentic_routes import agentic_api
from app.services.auth_service import User
from app.services.background_worker import background_worker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(watchlist_bp)
app.register_blueprint(stock_bp)
app.register_blueprint(prediction_bp)
app.register_blueprint(system_bp)
app.register_blueprint(agentic_api)

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))


# Start background worker when app starts
@app.before_request
def start_background_worker():
    """Start the background worker before every request."""
    background_worker.start()


if __name__ == '__main__':
    port = int(os.environ.get('FLASK_PORT', 5005))
    logger.info(f"Starting StockSense application on port {port}")
    app.run(host='0.0.0.0', debug=False, port=port)
