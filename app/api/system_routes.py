"""
System monitoring and management API routes
"""
import json
import logging
import time
from datetime import datetime

from flask import Blueprint, jsonify, request, Response
from flask_login import login_required

from app.services.background_worker import background_worker
from app.utils.disk_monitor import DiskSpaceMonitor

system_bp = Blueprint('system', __name__, url_prefix='/api/system')

# Track application start time for uptime calculation
app_start_time = datetime.now()


@system_bp.route('/status')
@login_required
def system_status():
    """Get system status including background worker and disk space"""
    worker_status = background_worker.get_status()
    disk_usage = DiskSpaceMonitor.get_disk_usage()
    model_stats = DiskSpaceMonitor.get_model_directory_size()
    
    return jsonify({
        'background_worker': worker_status,
        'disk_usage': disk_usage,
        'model_stats': model_stats
    }), 200


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
