from urllib.parse import urlparse
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db
from app.models.user import User
from app.models.student import Student
from app.blueprints.auth import auth_bp
from app.blueprints.auth.forms import LoginForm, SignupForm


def get_redirect_target(role):
    if role == 'admin':
        return url_for('admin.dashboard')
    elif role == 'student':
        return url_for('student.dashboard')
    elif role == 'employer':
        return url_for('employer.dashboard')
    return url_for('verify.landing')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(get_redirect_target(current_user.role))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        password = form.password.data
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=form.remember_me.data)
            flash(f'Welcome back, {user.name}!', 'success')

            # Handle next parameter safely
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = get_redirect_target(user.role)

            if request.is_json:
                return jsonify({
                    'success': True,
                    'redirect': next_page,
                    'user': user.to_dict()
                })

            return redirect(next_page)
        else:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Invalid email or password.'}), 401
            flash('Invalid email or password. Please try again.', 'error')

    if request.is_json and request.method == 'POST':
        errors = [f"{field}: {', '.join(errs)}" for field, errs in form.errors.items()]
        return jsonify({'success': False, 'errors': errors}), 400

    return render_template('auth/login.html', form=form)


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(get_redirect_target(current_user.role))

    form = SignupForm()
    if form.validate_on_submit():
        try:
            role = form.role.data
            user = User(
                name=form.name.data.strip(),
                email=form.email.data.lower().strip(),
                role=role,
                college_name=form.college_name.data.strip() if form.college_name.data else None
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()  # get user.id

            if role == 'student':
                student_profile = Student(
                    user_id=user.id,
                    roll_number=form.roll_number.data.strip() if form.roll_number.data else f"STU-{user.id:04d}",
                    degree=form.degree.data.strip() if form.degree.data else "General",
                    department=form.department.data.strip() if form.department.data else "General",
                    graduation_year=form.graduation_year.data or 2025,
                    cgpa=form.cgpa.data
                )
                db.session.add(student_profile)

            db.session.commit()
            login_user(user)
            flash('Account created successfully! Welcome to BlockCert.', 'success')

            target = get_redirect_target(user.role)
            if request.is_json:
                return jsonify({
                    'success': True,
                    'redirect': target,
                    'user': user.to_dict()
                }), 201

            return redirect(target)

        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)}), 500
            flash(f'An error occurred during signup: {str(e)}', 'error')

    if request.is_json and request.method == 'POST':
        errors = [f"{field}: {', '.join(errs)}" for field, errs in form.errors.items()]
        return jsonify({'success': False, 'errors': errors}), 400

    return render_template('auth/signup.html', form=form)


@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    if request.is_json:
        return jsonify({'success': True, 'redirect': url_for('auth.login')})
    return redirect(url_for('auth.login'))
