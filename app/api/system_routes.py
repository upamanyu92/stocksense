"""
System monitoring and management API routes
"""
import json
import logging
import os
import time
from datetime import datetime

from flask import Blueprint, jsonify, request, Response, render_template
from flask_login import login_required

from app.services.background_worker import background_worker
from app.utils.disk_monitor import DiskSpaceMonitor
from app.services.worker_config import load_config, save_config

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
        }, 200)
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


@system_bp.route('/digest/enable', methods=['POST'])
@login_required
def enable_digest():
    from flask_login import current_user
    from app.db.services.user_service import UserService
    user = UserService.get_by_id(current_user.id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'error': 'Admin privileges required'}), 403
    cfg = load_config()
    cfg['digest_email_enabled'] = True
    save_config(cfg)
    return jsonify({'success': True, 'digest_email_enabled': True}), 200


@system_bp.route('/digest/disable', methods=['POST'])
@login_required
def disable_digest():
    from flask_login import current_user
    from app.db.services.user_service import UserService
    user = UserService.get_by_id(current_user.id)
    if not user or not user.is_admin:
        return jsonify({'success': False, 'error': 'Admin privileges required'}), 403
    cfg = load_config()
    cfg['digest_email_enabled'] = False
    save_config(cfg)
    return jsonify({'success': True, 'digest_email_enabled': False}), 200


@system_bp.route('/digest/status', methods=['GET'])
@login_required
def digest_status():
    cfg = load_config()
    return jsonify({'digest_email_enabled': bool(cfg.get('digest_email_enabled', False))}), 200


def _save_worker_state(enabled: bool):
    """Save background worker state to configuration file"""
    # Preserve other flags when updating worker state
    cfg = load_config()
    cfg['background_worker_enabled'] = bool(enabled)
    save_config(cfg)


def _load_worker_state() -> bool:
    """Load background worker state from configuration file"""
    cfg = load_config()
    return bool(cfg.get('background_worker_enabled', False))


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


@system_bp.route('/integrations/status', methods=['GET'])
@login_required
def integrations_status():
    """
    Check connectivity and configuration for all external integrations.

    Returns a list of integration status objects, each with:
      - name         : Human-readable service name
      - key          : Machine-readable identifier
      - online       : True if reachable / configured, False otherwise
      - detail       : Short explanation (e.g. API key status, error message)
      - checked_at   : ISO-8601 timestamp of the check
    """
    from flask_login import current_user
    from app.db.services.user_service import UserService

    user = UserService.get_by_id(current_user.id)
    if not user or not user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403

    import importlib.util
    import os
    import requests as _req

    results = []
    now = datetime.now().isoformat()

    # ------------------------------------------------------------------
    # 1. GitHub Copilot AI (OpenAI-compatible endpoint)
    # ------------------------------------------------------------------
    try:
        github_token = os.getenv('GITHUB_TOKEN', '')
        copilot_model = os.getenv('COPILOT_MODEL', 'gpt-4o')
        openai_installed = importlib.util.find_spec('openai') is not None

        if not github_token:
            results.append({
                'name': 'Copilot AI',
                'key': 'copilot',
                'online': False,
                'detail': 'GITHUB_TOKEN not set',
                'checked_at': now,
            })
        elif not openai_installed:
            results.append({
                'name': 'Copilot AI',
                'key': 'copilot',
                'online': False,
                'detail': 'openai package not installed',
                'checked_at': now,
            })
        else:
            from app.agents.copilot_agent import CopilotClient
            client = CopilotClient()
            available = client.is_available()
            results.append({
                'name': 'Copilot AI',
                'key': 'copilot',
                'online': available,
                'detail': f'Token set, model={copilot_model}' if available else 'Endpoint unreachable',
                'checked_at': now,
            })
    except Exception as exc:
        results.append({
            'name': 'Copilot AI',
            'key': 'copilot',
            'online': False,
            'detail': f'Check failed: {str(exc)[:100]}',
            'checked_at': now,
        })

    # ------------------------------------------------------------------
    # 3. Google Gemini AI
    # ------------------------------------------------------------------
    try:
        gemini_key = os.getenv('GEMINI_API_KEY', '')
        gemini_model = os.getenv('GEMINI_MODEL_NAME', '')

        if not gemini_key:
            results.append({
                'name': 'Google Gemini AI',
                'key': 'gemini',
                'online': False,
                'detail': 'GEMINI_API_KEY not set',
                'checked_at': now,
            })
        else:
            # Probe the Gemini REST API with a minimal models list call
            probe_url = (
                f"https://generativelanguage.googleapis.com/v1beta/models"
                f"?key={gemini_key}"
            )
            resp = _req.get(probe_url, timeout=10)
            if resp.status_code == 200:
                results.append({
                    'name': 'Google Gemini AI',
                    'key': 'gemini',
                    'online': True,
                    'detail': f'Reachable – model={gemini_model or "default"}',
                    'checked_at': now,
                })
            else:
                results.append({
                    'name': 'Google Gemini AI',
                    'key': 'gemini',
                    'online': False,
                    'detail': f'API returned HTTP {resp.status_code}',
                    'checked_at': now,
                })
    except Exception as exc:
        results.append({
            'name': 'Google Gemini AI',
            'key': 'gemini',
            'online': False,
            'detail': f'Connection error: {str(exc)[:100]}',
            'checked_at': now,
        })

    # ------------------------------------------------------------------
    # 4. Ollama Local LLM
    # ------------------------------------------------------------------
    try:
        from app.config.ollama_config import OllamaConfig

        resp = _req.get(f"{OllamaConfig.OLLAMA_HOST}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m.get('name', '') for m in resp.json().get('models', [])]
            model_found = any(OllamaConfig.MODEL_NAME in m for m in models)
            results.append({
                'name': 'Ollama Local LLM',
                'key': 'ollama',
                'online': True,
                'detail': (
                    f'Running – model={OllamaConfig.MODEL_NAME} ✓'
                    if model_found
                    else f'Running – model={OllamaConfig.MODEL_NAME} not pulled yet'
                ),
                'checked_at': now,
            })
        else:
            results.append({
                'name': 'Ollama Local LLM',
                'key': 'ollama',
                'online': False,
                'detail': f'Ollama returned HTTP {resp.status_code}',
                'checked_at': now,
            })
    except Exception as exc:
        results.append({
            'name': 'Ollama Local LLM',
            'key': 'ollama',
            'online': False,
            'detail': f'Not reachable at {OllamaConfig.OLLAMA_HOST}: {str(exc)[:80]}',
            'checked_at': now,
        })

    # ------------------------------------------------------------------
    # 5. YFinance (Yahoo Finance)
    # ------------------------------------------------------------------
    try:
        import yfinance as yf
        ticker = yf.Ticker('MSFT')
        # fast_info raises if there is no connectivity or the symbol is bad
        price = ticker.fast_info.get('last_price') or ticker.fast_info.get('regularMarketPrice')
        results.append({
            'name': 'YFinance (Yahoo Finance)',
            'key': 'yfinance',
            'online': True,
            'detail': f'Reachable – last MSFT price: {price}',
            'checked_at': now,
        })
    except Exception as exc:
        results.append({
            'name': 'YFinance (Yahoo Finance)',
            'key': 'yfinance',
            'online': False,
            'detail': f'Error: {str(exc)[:100]}',
            'checked_at': now,
        })

    return jsonify({'integrations': results, 'checked_at': now}), 200


@system_bp.route('/ui', methods=['GET'])
@login_required
def admin_ui():
    from flask_login import current_user
    from app.db.services.user_service import UserService
    user = UserService.get_by_id(current_user.id)
    if not user or not user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    return render_template('admin_system.html')
