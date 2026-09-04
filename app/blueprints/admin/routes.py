import os
from pathlib import Path
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.student import Student
from app.models.certificate import Certificate
from app.models.verification_log import VerificationLog
from app.blueprints.admin import admin_bp
from app.blueprints.admin.forms import IssueCertificateForm, StudentForm
from app.utils.decorators import admin_required
from app.blockchain.hashing import compute_file_sha256
from app.blockchain.qr import generate_certificate_qr
from app.blockchain.contract import blockchain_client
from app.utils.errors import BlockchainError


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Metrics calculations
    total_certificates = Certificate.query.count()
    
    # Issued this month
    now = datetime.now(timezone.utc)
    first_day_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    issued_this_month = Certificate.query.filter(Certificate.created_at >= first_day_of_month).count()
    
    total_students = Student.query.count()
    verified_count = VerificationLog.query.filter_by(result='verified').count()

    # Recent certificate uploads
    recent_certificates = Certificate.query.order_by(Certificate.created_at.desc()).limit(8).all()

    # Blockchain connection status
    blockchain_connected = blockchain_client.is_connected()
    contract_configured = bool(blockchain_client.get_contract_address())

    return render_template(
        'admin/dashboard.html',
        total_certificates=total_certificates,
        issued_this_month=issued_this_month,
        total_students=total_students,
        verified_count=verified_count,
        recent_certificates=recent_certificates,
        blockchain_connected=blockchain_connected,
        contract_configured=contract_configured
    )


@admin_bp.route('/upload', methods=['GET'])
@login_required
@admin_required
def upload():
    form = IssueCertificateForm()
    students = Student.query.join(User).order_by(User.name.asc()).all()
    form.student_id.choices = [(s.id, f"{s.user.name} ({s.roll_number}) - {s.degree}") for s in students]

    issuer_address, _ = (None, None)
    try:
        issuer_address, _ = blockchain_client.get_issuer_account()
    except Exception:
        pass

    return render_template(
        'admin/issue_certificate.html',
        form=form,
        students=students,
        issuer_address=issuer_address,
        blockchain_connected=blockchain_client.is_connected()
    )


@admin_bp.route('/certificates/issue', methods=['POST'])
@login_required
@admin_required
def issue_certificate():
    form = IssueCertificateForm()
    students = Student.query.join(User).order_by(User.name.asc()).all()
    form.student_id.choices = [(s.id, f"{s.user.name} ({s.roll_number}) - {s.degree}") for s in students]

    if not form.validate_on_submit():
        if request.is_json:
            errors = [f"{k}: {', '.join(v)}" for k, v in form.errors.items()]
            return jsonify({'success': False, 'errors': errors}), 400
        for field, errs in form.errors.items():
            for err in errs:
                flash(f"{field}: {err}", 'error')
        return redirect(url_for('admin.upload'))

    file_to_cleanup = None
    qr_to_cleanup = None

    try:
        student = Student.query.get_or_404(form.student_id.data)
        cert_id = form.certificate_id.data.strip()
        course = form.course.data.strip()
        grad_year = form.graduation_year.data
        uploaded_file = form.certificate_file.data

        # 1. Save uploaded file securely
        upload_dir = Path(current_app.config['UPLOAD_FOLDER'])
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        orig_filename = secure_filename(uploaded_file.filename)
        ext = orig_filename.rsplit('.', 1)[1].lower() if '.' in orig_filename else 'pdf'
        safe_cert_id_filename = f"{secure_filename(cert_id)}.{ext}"
        saved_file_path = upload_dir / safe_cert_id_filename

        uploaded_file.save(str(saved_file_path))
        file_to_cleanup = saved_file_path

        # 2. Compute SHA-256 fingerprint from actual saved file
        sha256_hash = compute_file_sha256(str(saved_file_path))

        # 3. Call Solidity smart contract on Ganache
        tx_result = blockchain_client.issue_certificate_onchain(cert_id, sha256_hash)
        tx_hash = tx_result['tx_hash']

        # 4. Generate QR code pointing to public verification URL
        qr_dir = Path(current_app.config['QR_FOLDER'])
        qr_dir.mkdir(parents=True, exist_ok=True)
        
        # Build base verification URL
        verify_url = url_for('verify.verify_certificate_view', certificate_id=cert_id, _external=True)
        qr_file_path = generate_certificate_qr(cert_id, verify_url, str(qr_dir))
        qr_to_cleanup = Path(qr_file_path)

        # 5. Persist DB record in transaction
        # Relative paths for portable static serving
        rel_file_path = f"uploads/certificates/{safe_cert_id_filename}"
        rel_qr_path = f"uploads/qrcodes/{Path(qr_file_path).name}"

        certificate = Certificate(
            certificate_id=cert_id,
            student_id=student.id,
            issuer_id=current_user.id,
            course=course,
            graduation_year=grad_year,
            file_path=rel_file_path,
            sha256_hash=sha256_hash,
            blockchain_tx_hash=tx_hash,
            qr_code_path=rel_qr_path,
            status='issued'
        )
        db.session.add(certificate)
        db.session.commit()

        flash(f"Certificate {cert_id} successfully minted on-chain! Tx: {tx_hash[:16]}...", 'success')

        if request.is_json:
            return jsonify({
                'success': True,
                'certificate': certificate.to_dict(),
                'tx_hash': tx_hash,
                'sha256_hash': sha256_hash,
                'qr_url': url_for('static', filename=rel_qr_path, _external=True),
                'verify_url': verify_url
            }), 201

        return redirect(url_for('admin.certificates_list'))

    except BlockchainError as be:
        db.session.rollback()
        # Clean up files on blockchain failure
        if file_to_cleanup and file_to_cleanup.exists():
            try:
                file_to_cleanup.unlink()
            except Exception:
                pass
        if qr_to_cleanup and qr_to_cleanup.exists():
            try:
                qr_to_cleanup.unlink()
            except Exception:
                pass

        flash(f"Blockchain Issuance Error: {be.message}", 'error')
        if request.is_json:
            return jsonify({'success': False, 'error': be.message}), 502
        return redirect(url_for('admin.upload'))

    except Exception as e:
        db.session.rollback()
        if file_to_cleanup and file_to_cleanup.exists():
            try:
                file_to_cleanup.unlink()
            except Exception:
                pass
        if qr_to_cleanup and qr_to_cleanup.exists():
            try:
                qr_to_cleanup.unlink()
            except Exception:
                pass

        flash(f"Error issuing certificate: {str(e)}", 'error')
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        return redirect(url_for('admin.upload'))


@admin_bp.route('/certificates')
@login_required
@admin_required
def certificates_list():
    search = request.args.get('search', '').strip()
    query = Certificate.query.join(Student).join(User, Student.user_id == User.id)

    if search:
        query = query.filter(
            db.or_(
                Certificate.certificate_id.ilike(f"%{search}%"),
                Certificate.course.ilike(f"%{search}%"),
                User.name.ilike(f"%{search}%"),
                Student.roll_number.ilike(f"%{search}%")
            )
        )

    certificates = query.order_by(Certificate.created_at.desc()).all()

    if request.is_json:
        return jsonify({
            'success': True,
            'count': len(certificates),
            'certificates': [c.to_dict() for c in certificates]
        })

    return render_template('admin/certificates.html', certificates=certificates, search=search)


@admin_bp.route('/students', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_students():
    form = StudentForm()
    if form.validate_on_submit():
        try:
            # Create user account
            user = User(
                name=form.name.data.strip(),
                email=form.email.data.lower().strip(),
                role='student',
                college_name=current_user.college_name or "BlockCert Academy"
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()

            # Create student record
            student = Student(
                user_id=user.id,
                roll_number=form.roll_number.data.strip(),
                degree=form.degree.data.strip(),
                department=form.department.data.strip(),
                graduation_year=form.graduation_year.data,
                cgpa=form.cgpa.data
            )
            db.session.add(student)
            db.session.commit()

            flash(f"Student '{user.name}' ({student.roll_number}) registered successfully!", 'success')
            return redirect(url_for('admin.manage_students'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error registering student: {str(e)}", 'error')

    students = Student.query.join(User).order_by(Student.id.desc()).all()

    if request.is_json and request.method == 'GET':
        return jsonify({
            'success': True,
            'students': [s.to_dict() for s in students]
        })

    return render_template('admin/students.html', form=form, students=students)
