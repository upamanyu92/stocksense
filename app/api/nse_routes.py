"""
API endpoints for NSE securities management
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required
import logging
import os

from app.services.nse_securities_service import NSESecuritiesService
from app.db.session_manager import get_session_manager

logger = logging.getLogger(__name__)

nse_bp = Blueprint('nse', __name__, url_prefix='/api/nse')


@nse_bp.route('/load-securities', methods=['POST'])
@login_required
def load_securities():
    """
    Load NSE securities from stk.json into database.

    Returns:
        JSON with load results
    """
    try:
        # Get stk.json path from project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        stk_file = os.path.join(project_root, 'stk.json')

        logger.info(f"Loading NSE securities from {stk_file}")

        # Load securities from file
        nse_service = NSESecuritiesService()
        securities = nse_service.load_nse_securities_from_file(stk_file)

        if not securities:
            return jsonify({
                'success': False,
                'error': f'Could not load securities from {stk_file}',
                'message': 'Please ensure stk.json exists in project root'
            }), 400

        # Add to database using pooled connection
        db = get_session_manager()
        conn = db.get_connection()
        try:
            result = nse_service.add_securities_to_db(securities, conn)
        finally:
            db.release_connection(conn)

        return jsonify({
            'success': result['success'],
            'message': f"Loaded {result.get('added', 0)} NSE securities ({result.get('skipped', 0)} skipped)",
            'details': result
        })

    except Exception as e:
        logger.error(f"Error loading securities: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@nse_bp.route('/count', methods=['GET'])
@login_required
def get_securities_count():
    """Get total count of NSE securities in database"""
    try:
        nse_service = NSESecuritiesService()
        db = get_session_manager()
        conn = db.get_connection()
        try:
            count = nse_service.get_security_count(conn)
        finally:
            db.release_connection(conn)

        return jsonify({
            'success': True,
            'count': count,
            'message': f'Total {count} securities in database'
        })

    except Exception as e:
        logger.error(f"Error getting count: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@nse_bp.route('/search', methods=['GET'])
@login_required
def search_securities():
    """
    Search for NSE securities by name or code.

    Query params:
        q: Search query
        limit: Number of results (default: 10, max: 50)

    Returns:
        List of matching securities
    """
    try:
        query = request.args.get('q', '').strip()
        limit = request.args.get('limit', 10, type=int)
        limit = min(limit, 50)  # Cap at 50

        if not query or len(query) < 2:
            return jsonify({
                'success': False,
                'error': 'Search query must be at least 2 characters'
            }), 400

        nse_service = NSESecuritiesService()
        db = get_session_manager()
        conn = db.get_connection()
        try:
            securities = nse_service.search_securities(conn, query)
        finally:
            db.release_connection(conn)

        return jsonify({
            'success': True,
            'query': query,
            'count': len(securities),
            'securities': securities
        })

    except Exception as e:
        logger.error(f"Error searching securities: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@nse_bp.route('/list', methods=['GET'])
@login_required
def list_securities():
    """
    List available NSE securities.

    Query params:
        limit: Number of results (default: 20, max: 100)

    Returns:
        List of securities
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 100)  # Cap at 100

        nse_service = NSESecuritiesService()
        db = get_session_manager()
        conn = db.get_connection()
        try:
            securities = nse_service.get_available_securities(conn, limit=limit)
            total_count = nse_service.get_security_count(conn)
        finally:
            db.release_connection(conn)

        return jsonify({
            'success': True,
            'total_count': total_count,
            'returned': len(securities),
            'securities': securities
        })

    except Exception as e:
        logger.error(f"Error listing securities: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

