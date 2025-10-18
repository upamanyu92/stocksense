"""
Dashboard and UI routes
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def user_dashboard():
    """User dashboard page"""
    return render_template('dashboard.html', username=current_user.username)
