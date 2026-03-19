"""
Dashboard and UI routes
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.db.services.user_service import UserService

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def user_dashboard():
    """User dashboard page"""
    return render_template('dashboard.html', username=current_user.username)


@dashboard_bp.route('/stocks')
@login_required
def stocks_list():
    """Stocks list page with pagination and sorting"""
    return render_template('stocks_list.html', username=current_user.username)


@dashboard_bp.route('/notifications')
@login_required
def notifications_page():
    """Notifications page"""
    return render_template('notifications.html', username=current_user.username)


@dashboard_bp.route('/alerts')
@login_required
def alerts_page():
    """Alerts management page"""
    return render_template('alerts_mgmt.html', username=current_user.username)


@dashboard_bp.route('/admin')
@login_required
def admin_page():
    """System administration page (admin users only)"""
    user = UserService.get_by_id(current_user.id)
    if not user or not user.is_admin:
        from flask import abort
        abort(403)
    return render_template('admin_system.html', username=current_user.username)
