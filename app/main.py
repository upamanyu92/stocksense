# Main Flask application entry point
import logging
import os
from datetime import datetime

from flask import Flask, jsonify
from flask_cors import CORS
from flask_login import LoginManager
from flask_socketio import SocketIO, emit

from app.api.auth_routes import auth_bp
from app.api.watchlist_routes import watchlist_bp
from app.api.prediction_routes import prediction_bp
from app.api.stock_routes import stock_bp
from app.api.system_routes import system_bp
from app.api.price_stream_routes import price_stream_bp
from app.api.dashboard_routes import dashboard_bp
from app.services.auth_service import User
from app.services.background_worker import background_worker
from app.services.price_streamer import price_streamer
from app.utils.disk_monitor import DiskSpaceMonitor
from app.utils.websocket_manager import websocket_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize WebSocket manager
websocket_manager.init_socketio(socketio)

# Set websocket manager in background worker
from app.services import background_worker as bg_worker_module
bg_worker_module.set_websocket_manager(websocket_manager)

# Set websocket manager in price streamer
price_streamer.set_websocket_manager(websocket_manager)

# Set websocket manager in prediction service
from app.services import prediction_service as pred_service_module
pred_service_module.set_websocket_manager(websocket_manager)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(watchlist_bp)
app.register_blueprint(prediction_bp)
app.register_blueprint(stock_bp)
app.register_blueprint(system_bp)
app.register_blueprint(price_stream_bp)
app.register_blueprint(dashboard_bp)

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))

# Start background worker when app starts
@app.before_request
def start_background_worker():
    """Start the background worker before every request"""
    background_worker.start()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker and monitoring"""
    return jsonify({"status": "healthy", "service": "stocksense"}), 200

@app.route('/')
def root():
    """Root endpoint redirects to dashboard"""
    from flask import redirect, url_for
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.user_dashboard'))
    return redirect(url_for('auth.login'))

# WebSocket event handlers for real-time updates
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    from flask import request
    logging.info(f"Client connected: {request.sid}")
    emit('connection_status', {'status': 'connected', 'message': 'Connected to StockSense'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    from flask import request
    logging.info(f"Client disconnected: {request.sid}")

@socketio.on('subscribe_predictions')
def handle_subscribe_predictions():
    """Subscribe to real-time prediction updates"""
    from flask import request
    logging.info(f"Client {request.sid} subscribed to prediction updates")
    emit('subscription_confirmed', {'type': 'predictions'})

@socketio.on('subscribe_watchlist')
def handle_subscribe_watchlist(data=None):
    """Subscribe to real-time watchlist updates"""
    from flask import request
    user_id = data.get('user_id') if data else None
    logging.info(f"Client {request.sid} subscribed to watchlist updates for user {user_id}")
    emit('subscription_confirmed', {'type': 'watchlist'})

@socketio.on('subscribe_stock_prices')
def handle_subscribe_stock_prices(data):
    """Subscribe to real-time stock price updates"""
    from flask import request
    symbols = data.get('symbols', []) if data else []
    logging.info(f"Client {request.sid} subscribed to price updates for {len(symbols)} stocks")
    
    # Add symbols to price streamer
    for symbol in symbols:
        price_streamer.add_symbol(symbol)
    
    # Start streaming if not already running
    if not price_streamer.streaming:
        price_streamer.start_streaming()
    
    emit('subscription_confirmed', {'type': 'stock_prices', 'symbols': symbols})

@socketio.on('unsubscribe_stock_prices')
def handle_unsubscribe_stock_prices(data):
    """Unsubscribe from stock price updates"""
    from flask import request
    symbols = data.get('symbols', []) if data else []
    logging.info(f"Client {request.sid} unsubscribed from price updates for {len(symbols)} stocks")
    
    # Remove symbols from price streamer
    for symbol in symbols:
        price_streamer.remove_symbol(symbol)
    
    emit('unsubscription_confirmed', {'type': 'stock_prices', 'symbols': symbols})

@socketio.on('request_system_status')
def handle_system_status_request():
    """Send current system status via WebSocket"""
    worker_status = background_worker.get_status()
    disk_usage = DiskSpaceMonitor.get_disk_usage()
    model_stats = DiskSpaceMonitor.get_model_directory_size()
    
    emit('system_status', {
        'background_worker': worker_status,
        'disk_usage': disk_usage,
        'model_stats': model_stats
    })

if __name__ == '__main__':
    port = int(os.environ.get('FLASK_PORT', 5005))
    logging.info(f"Starting StockSense application on port {port}")
    socketio.run(app, host='0.0.0.0', debug=False, port=port, allow_unsafe_werkzeug=True)
