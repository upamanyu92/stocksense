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
from app.services.inactive_stock_worker import inactive_stock_worker
from app.services.worker_settings_service import WorkerSettingsService
from app.utils.disk_monitor import DiskSpaceMonitor

system_bp = Blueprint('system', __name__, url_prefix='/api/system')

# Track application start time for uptime calculation
app_start_time = datetime.now()

# Worker instance mapping
WORKER_INSTANCES = {
    'background_worker': background_worker,
    'inactive_stock_worker': inactive_stock_worker
}


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


@system_bp.route('/workers/settings', methods=['GET'])
@login_required
def get_worker_settings():
    """Get settings for all workers"""
    try:
        settings = WorkerSettingsService.get_all_worker_settings()

        # Add runtime status
        result = {
            'background_worker': {
                'enabled': settings.get('background_worker', {}).get('enabled', True),
                'running': background_worker.running,
                'updated_at': settings.get('background_worker', {}).get('updated_at')
            },
            'inactive_stock_worker': {
                'enabled': settings.get('inactive_stock_worker', {}).get('enabled', True),
                'running': inactive_stock_worker.running,
                'updated_at': settings.get('inactive_stock_worker', {}).get('updated_at')
            }
        }

        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error getting worker settings: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to retrieve worker settings'
        }), 500


@system_bp.route('/workers/<worker_name>/enable', methods=['POST'])
@login_required
def enable_worker(worker_name):
    """Enable a background worker"""
    try:
        if worker_name not in ['background_worker', 'inactive_stock_worker']:
            return jsonify({
                'success': False,
                'error': 'Invalid worker name'
            }), 400

        # Update database configuration
        result = WorkerSettingsService.set_worker_enabled(worker_name, True)

        if not result.get('success'):
            return jsonify(result), 500

        # Start the worker if it's not already running
        worker = WORKER_INSTANCES[worker_name]
        if not worker.running:
            worker.start()

        is_running = worker.running
        return jsonify({
            'success': True,
            'worker_name': worker_name,
            'enabled': True,
            'running': is_running
        }), 200

    except Exception as e:
        logging.error(f"Error enabling worker {worker_name}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to enable worker'
        }), 500


@system_bp.route('/workers/<worker_name>/disable', methods=['POST'])
@login_required
def disable_worker(worker_name):
    """Disable a background worker"""
    try:
        if worker_name not in ['background_worker', 'inactive_stock_worker']:
            return jsonify({
                'success': False,
                'error': 'Invalid worker name'
            }), 400

        # Update database configuration
        result = WorkerSettingsService.set_worker_enabled(worker_name, False)

        if not result.get('success'):
            return jsonify(result), 500

        # Stop the worker if it's running
        worker = WORKER_INSTANCES[worker_name]
        if worker.running:
            worker.stop()

        is_running = worker.running
        return jsonify({
            'success': True,
            'worker_name': worker_name,
            'enabled': False,
            'running': is_running
        }), 200

    except Exception as e:
        logging.error(f"Error disabling worker {worker_name}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to disable worker'
        }), 500
