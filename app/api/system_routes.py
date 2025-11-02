"""
System monitoring and management API routes
"""
import json
import logging
import os
import time
from datetime import datetime

from flask import Blueprint, jsonify, request, Response
from flask_login import login_required

from app.services.background_worker import background_worker
from app.utils.disk_monitor import DiskSpaceMonitor

system_bp = Blueprint('system', __name__, url_prefix='/api/system')

# Track application start time for uptime calculation
app_start_time = datetime.now()

# Configuration file path
WORKER_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'worker_config.json')


@system_bp.route('/status')
@login_required
def system_status():
    """Get system status including background worker and disk space"""
    try:
        worker_status = background_worker.get_status()
        disk_usage = DiskSpaceMonitor.get_disk_usage()
        model_stats = DiskSpaceMonitor.get_model_directory_size()

        return jsonify({
            'background_worker': worker_status,
            'disk_usage': disk_usage,
            'model_stats': model_stats
        }), 200
    except Exception as e:
        logging.error(f"Error getting system status: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to retrieve system status'
        }), 500


@system_bp.route('/uptime')
@login_required
def get_uptime():
    """Get application uptime"""
    uptime_seconds = (datetime.now() - app_start_time).total_seconds()
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    
    uptime_str = ""
    if days > 0:
        uptime_str += f"{days}d "
    if hours > 0 or days > 0:
        uptime_str += f"{hours}h "
    uptime_str += f"{minutes}m"
    
    return jsonify({
        'uptime': uptime_str,
        'uptime_seconds': int(uptime_seconds)
    }), 200


@system_bp.route('/cleanup_models', methods=['POST'])
@login_required
def cleanup_models():
    """Cleanup old models"""
    try:
        keep_newest = request.json.get('keep_newest', 2) if request.json else 2
        result = DiskSpaceMonitor.cleanup_old_models(keep_newest)
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        logging.error(f"Error cleaning up models: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to cleanup models'
        }), 500


@system_bp.route('/background_worker/start', methods=['POST'])
@login_required
def start_background_worker():
    """Start the background worker (admin only)"""
    from flask_login import current_user
    from app.db.services.user_service import UserService
    
    # Check if user is admin
    user = UserService.get_by_id(current_user.id)
    if not user or not user.is_admin:
        return jsonify({
            'success': False,
            'error': 'Admin privileges required'
        }), 403
    
    try:
        background_worker.start()
        # Save worker state to config
        _save_worker_state(True)
        return jsonify({
            'success': True,
            'message': 'Background worker started'
        }), 200
    except Exception as e:
        logging.error(f"Error starting background worker: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/background_worker/stop', methods=['POST'])
@login_required
def stop_background_worker():
    """Stop the background worker (admin only)"""
    from flask_login import current_user
    from app.db.services.user_service import UserService
    
    # Check if user is admin
    user = UserService.get_by_id(current_user.id)
    if not user or not user.is_admin:
        return jsonify({
            'success': False,
            'error': 'Admin privileges required'
        }), 403
    
    try:
        background_worker.stop()
        # Save worker state to config
        _save_worker_state(False)
        return jsonify({
            'success': True,
            'message': 'Background worker stopped'
        }), 200
    except Exception as e:
        logging.error(f"Error stopping background worker: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _save_worker_state(enabled: bool):
    """Save background worker state to configuration file"""
    os.makedirs(os.path.dirname(WORKER_CONFIG_PATH), exist_ok=True)
    
    with open(WORKER_CONFIG_PATH, 'w') as f:
        json.dump({'background_worker_enabled': enabled}, f)


def _load_worker_state() -> bool:
    """Load background worker state from configuration file"""
    if os.path.exists(WORKER_CONFIG_PATH):
        try:
            with open(WORKER_CONFIG_PATH, 'r') as f:
                config = json.load(f)
                return config.get('background_worker_enabled', False)
        except Exception as e:
            logging.error(f"Error loading worker config: {str(e)}")
    
    return False  # Default to disabled


@system_bp.route('/background_worker/status')
@login_required
def background_worker_status():
    """Get background worker status stream"""
    def event_stream():
        while True:
            status = background_worker.get_status()
            yield f"data: {json.dumps(status)}\n\n"
            time.sleep(2)
    return Response(event_stream(), mimetype="text/event-stream")


@system_bp.route('/background-status', methods=['GET'])
def background_status():
    """Return real-time status of background worker"""
    return jsonify(background_worker.get_status())
