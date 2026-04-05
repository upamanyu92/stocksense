"""
Settings and onboarding API routes - manages user preferences,
onboarding flow, and model status.
"""
import logging

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app.services.user_settings_service import UserSettingsService
from app.services.portfolio_analysis_service import PortfolioAnalysisService

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')


# ------------------------------------------------------------------ #
#  User Settings
# ------------------------------------------------------------------ #

@settings_bp.route('/', methods=['GET'])
@login_required
def get_settings():
    """Get user settings."""
    try:
        settings = UserSettingsService.get_settings(current_user.id)
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        logger.error(f"Error fetching settings: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch settings'}), 500


@settings_bp.route('/', methods=['PUT'])
@login_required
def update_settings():
    """Update user settings."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        updated = UserSettingsService.update_settings(current_user.id, data)
        if not updated:
            return jsonify({'error': 'No valid fields to update'}), 400

        settings = UserSettingsService.get_settings(current_user.id)
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        logger.error(f"Error updating settings: {e}", exc_info=True)
        return jsonify({'error': 'Failed to update settings'}), 500


# ------------------------------------------------------------------ #
#  Onboarding
# ------------------------------------------------------------------ #

@settings_bp.route('/onboarding', methods=['GET'])
@login_required
def get_onboarding():
    """Get onboarding status."""
    try:
        status = UserSettingsService.get_onboarding_status(current_user.id)
        return jsonify({'success': True, **status})
    except Exception as e:
        logger.error(f"Error fetching onboarding status: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch onboarding status'}), 500


@settings_bp.route('/onboarding/advance', methods=['POST'])
@login_required
def advance_onboarding():
    """Advance to the next onboarding step."""
    try:
        data = request.get_json() or {}
        step = data.get('step')
        status = UserSettingsService.advance_onboarding(current_user.id, step)
        return jsonify({'success': True, **status})
    except Exception as e:
        logger.error(f"Error advancing onboarding: {e}", exc_info=True)
        return jsonify({'error': 'Failed to advance onboarding'}), 500


@settings_bp.route('/onboarding/skip', methods=['POST'])
@login_required
def skip_onboarding():
    """Skip the entire onboarding process."""
    try:
        UserSettingsService.skip_onboarding(current_user.id)
        return jsonify({'success': True, 'message': 'Onboarding skipped'})
    except Exception as e:
        logger.error(f"Error skipping onboarding: {e}", exc_info=True)
        return jsonify({'error': 'Failed to skip onboarding'}), 500


# ------------------------------------------------------------------ #
#  Model Status
# ------------------------------------------------------------------ #

@settings_bp.route('/model-status', methods=['GET'])
@login_required
def get_model_status():
    """Get AI model availability status."""
    try:
        status = PortfolioAnalysisService.get_model_status()
        return jsonify({'success': True, **status})
    except Exception as e:
        logger.error(f"Error fetching model status: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch model status'}), 500


# ------------------------------------------------------------------ #
#  AI Portfolio Analysis
# ------------------------------------------------------------------ #

@settings_bp.route('/portfolio-analysis', methods=['POST'])
@login_required
def portfolio_analysis():
    """Generate AI portfolio analysis."""
    try:
        data = request.get_json() or {}
        analysis_type = data.get('type', 'summary')
        force_refresh = data.get('force_refresh', False)

        if analysis_type not in ('summary', 'risk', 'allocation', 'recommendation'):
            return jsonify({'error': 'Invalid analysis type'}), 400

        result = PortfolioAnalysisService.analyze_portfolio(
            current_user.id, analysis_type, force_refresh,
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error generating analysis: {e}", exc_info=True)
        return jsonify({'error': 'Failed to generate analysis'}), 500
