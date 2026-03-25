"""
Authentication routes for login/logout functionality.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse, urljoin
from app.services.auth_service import User

auth_bp = Blueprint('auth', __name__)


def _is_safe_redirect_url(target: str) -> bool:
    """Return True only if the redirect target is a local URL."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler"""
    if current_user.is_authenticated:
        return redirect(url_for('premium_dashboard.premium_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please provide both username and password', 'error')
            return render_template('login.html')
        
        # Verify credentials
        if User.verify_password(username, password):
            user = User.get_by_username(username)
            if user and user.is_active:
                login_user(user, remember=True)
                
                # Redirect to next page or dashboard
                next_page = request.args.get('next')
                if next_page and _is_safe_redirect_url(next_page):
                    return redirect(next_page)
                return redirect(url_for('premium_dashboard.premium_dashboard'))
            else:
                flash('User account is inactive', 'error')
        else:
            flash('Invalid username or password', 'error')
        
        return render_template('login.html')
    
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout handler"""
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page (optional)"""
    if current_user.is_authenticated:
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        # Create user
        user = User.create_user(username, password, email)
        if user:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Username already exists or registration failed', 'error')
    
    return render_template('register.html')
