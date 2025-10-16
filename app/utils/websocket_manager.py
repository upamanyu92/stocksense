"""
WebSocket manager for real-time updates across the application.
This module provides a centralized way to emit WebSocket events.
"""
import logging
from typing import Any, Dict


class WebSocketManager:
    """Manages WebSocket connections and event emissions"""
    
    def __init__(self):
        self.socketio = None
        
    def init_socketio(self, socketio):
        """Initialize with SocketIO instance"""
        self.socketio = socketio
        logging.info("WebSocket manager initialized")
        
    def emit_prediction_update(self, prediction_data: Dict[str, Any]):
        """Emit real-time prediction update"""
        if self.socketio:
            self.socketio.emit('prediction_update', prediction_data)
            logging.debug(f"Emitted prediction update: {prediction_data.get('company_name', 'Unknown')}")
    
    def emit_watchlist_update(self, watchlist_data: Dict[str, Any]):
        """Emit real-time watchlist update"""
        if self.socketio:
            self.socketio.emit('watchlist_update', watchlist_data)
            logging.debug("Emitted watchlist update")
    
    def emit_stock_price_update(self, price_data: Dict[str, Any]):
        """Emit real-time stock price update"""
        if self.socketio:
            self.socketio.emit('stock_price_update', price_data)
            logging.debug(f"Emitted price update: {price_data.get('symbol', 'Unknown')}")
    
    def emit_background_worker_status(self, status_data: Dict[str, Any]):
        """Emit background worker status update"""
        if self.socketio:
            self.socketio.emit('background_worker_status', status_data)
            logging.debug("Emitted background worker status")
    
    def emit_system_alert(self, alert_data: Dict[str, Any]):
        """Emit system alert (disk space, errors, etc.)"""
        if self.socketio:
            self.socketio.emit('system_alert', alert_data)
            logging.info(f"Emitted system alert: {alert_data.get('message', 'Unknown')}")
    
    def emit_prediction_progress(self, progress_data: Dict[str, Any]):
        """Emit prediction progress update"""
        if self.socketio:
            self.socketio.emit('prediction_progress', progress_data)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
