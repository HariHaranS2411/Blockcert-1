from functools import wraps
from flask import abort, flash, redirect, url_for, request, jsonify
from flask_login import current_user


def role_required(*roles):
    """
    Decorator to restrict access to users with specific roles.
    Example: @role_required('admin') or @role_required('admin', 'employer')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': 'Authentication required'}), 401
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            if current_user.role not in roles:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': 'Permission denied: unauthorized role'}), 403
                flash('You do not have permission to access this page.', 'error')
                # Redirect to user's appropriate dashboard
                if current_user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif current_user.role == 'student':
                    return redirect(url_for('student.dashboard'))
                elif current_user.role == 'employer':
                    return redirect(url_for('employer.dashboard'))
                return redirect(url_for('auth.login'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    return role_required('admin')(f)


def student_required(f):
    return role_required('student')(f)


def employer_required(f):
    return role_required('employer')(f)
