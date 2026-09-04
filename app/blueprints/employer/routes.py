from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models.certificate import Certificate
from app.models.verification_log import VerificationLog
from app.blueprints.employer import employer_bp
from app.blueprints.employer.forms import CertificateSearchForm
from app.utils.decorators import employer_required


@employer_bp.route('/dashboard')
@login_required
@employer_required
def dashboard():
    form = CertificateSearchForm()
    recent_searches = VerificationLog.query.filter_by(
        verifier_id=current_user.id
    ).order_by(VerificationLog.created_at.desc()).limit(10).all()

    total_verified = VerificationLog.query.filter_by(verifier_id=current_user.id, result='verified').count()
    total_searches = VerificationLog.query.filter_by(verifier_id=current_user.id).count()

    return render_template(
        'employer/dashboard.html',
        form=form,
        recent_searches=recent_searches,
        total_verified=total_verified,
        total_searches=total_searches
    )


@employer_bp.route('/search', methods=['POST'])
@login_required
@employer_required
def search():
    form = CertificateSearchForm()
    if form.validate_on_submit():
        cert_id = form.certificate_id.data.strip()
        if request.is_json:
            return jsonify({
                'success': True,
                'redirect': url_for('verify.verify_certificate_view', certificate_id=cert_id)
            })
        return redirect(url_for('verify.verify_certificate_view', certificate_id=cert_id))

    if request.is_json:
        return jsonify({'success': False, 'errors': form.errors}), 400
    
    flash('Please enter a valid Certificate ID.', 'error')
    return redirect(url_for('employer.dashboard'))


@employer_bp.route('/history')
@login_required
@employer_required
def history():
    logs = VerificationLog.query.filter_by(
        verifier_id=current_user.id
    ).order_by(VerificationLog.created_at.desc()).all()

    if request.is_json:
        return jsonify({
            'success': True,
            'count': len(logs),
            'history': [l.to_dict() for l in logs]
        })

    return render_template('employer/history.html', logs=logs)
