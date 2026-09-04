import os
import json
from pathlib import Path
from flask import render_template, abort, send_file, current_app, jsonify, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.certificate import Certificate
from app.models.resume import Resume
from app.blueprints.student import student_bp
from app.utils.decorators import student_required
from app.services.ai_resume_service import AIResumeService


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    student = current_user.student_profile
    if not student:
        flash("Student profile not found. Please contact administration.", "error")
        certificates = []
    else:
        certificates = Certificate.query.filter_by(student_id=student.id).order_by(Certificate.created_at.desc()).all()

    total_certificates = len(certificates)
    verified_certificates = sum(1 for c in certificates if c.status == 'issued')

    return render_template(
        'student/dashboard.html',
        student=student,
        certificates=certificates,
        total_certificates=total_certificates,
        verified_certificates=verified_certificates
    )


@student_bp.route('/certificates')
@login_required
@student_required
def certificates_list():
    student = current_user.student_profile
    if not student:
        return jsonify({'success': False, 'error': 'Student profile not found'}), 404

    certificates = Certificate.query.filter_by(student_id=student.id).order_by(Certificate.created_at.desc()).all()
    return jsonify({
        'success': True,
        'count': len(certificates),
        'certificates': [c.to_dict() for c in certificates]
    })


@student_bp.route('/certificates/<certificate_id>/download')
@login_required
def download_certificate(certificate_id):
    cert = Certificate.query.filter_by(certificate_id=certificate_id).first_or_404()

    # Access control: only the certificate's student or an admin can download
    if current_user.is_student:
        if not current_user.student_profile or cert.student_id != current_user.student_profile.id:
            abort(403)
    elif not current_user.is_admin:
        abort(403)

    base_dir = Path(current_app.root_path)
    file_path = base_dir / 'static' / cert.file_path
    
    if not file_path.exists():
        file_path = Path(current_app.config['UPLOAD_FOLDER']) / Path(cert.file_path).name
        if not file_path.exists():
            abort(404, description="Certificate document file not found on server.")

    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=f"{cert.certificate_id}_{Path(cert.file_path).name}"
    )


@student_bp.route('/certificates/<certificate_id>/qr')
@login_required
def get_qr_code(certificate_id):
    cert = Certificate.query.filter_by(certificate_id=certificate_id).first_or_404()

    # Access control
    if current_user.is_student:
        if not current_user.student_profile or cert.student_id != current_user.student_profile.id:
            abort(403)
    elif not (current_user.is_admin or current_user.is_employer):
        abort(403)

    base_dir = Path(current_app.root_path)
    qr_path = base_dir / 'static' / cert.qr_code_path
    
    if not qr_path.exists():
        qr_path = Path(current_app.config['QR_FOLDER']) / Path(cert.qr_code_path).name
        if not qr_path.exists():
            abort(404, description="QR code image not found.")

    return send_file(str(qr_path), mimetype='image/png')


# ==========================================
# AI RESUME MAKER ROUTES
# ==========================================

@student_bp.route('/resume')
@login_required
@student_required
def resume_builder():
    student = current_user.student_profile
    if not student:
        flash("Student profile not found.", "error")
        return redirect(url_for('student.dashboard'))

    # Fetch verified BlockCert certificates
    certificates = Certificate.query.filter_by(student_id=student.id, status='issued').all()

    # Load existing saved resume or initialize default template
    saved_resume = Resume.query.filter_by(student_id=student.id).first()
    resume_data = saved_resume.data if saved_resume else None

    cgpa_val = student.cgpa
    cgpa_strategy = AIResumeService.analyze_cgpa_strategy(cgpa_val)
    extracted_skills = AIResumeService.extract_skills_from_certificates(certificates)

    return render_template(
        'student/resume_builder.html',
        student=student,
        certificates=certificates,
        resume_data=resume_data,
        cgpa_strategy=cgpa_strategy,
        extracted_skills=extracted_skills
    )


@student_bp.route('/resume/interview', methods=['POST'])
@login_required
@student_required
def resume_interview():
    """
    Conversational AI interview endpoint.
    Conducts interactive multi-step questioning to assemble the student's resume.
    """
    data = request.get_json() or {}
    step = int(data.get('step', 0))
    user_message = data.get('message', '').strip()
    current_state = data.get('state', {})

    student = current_user.student_profile
    certificates = Certificate.query.filter_by(student_id=student.id, status='issued').all() if student else []

    response = AIResumeService.conduct_interview_step(
        step=step,
        user_message=user_message,
        current_state=current_state,
        student_profile=student,
        certificates=certificates
    )

    return jsonify({
        'success': True,
        **response
    })


@student_bp.route('/resume/polish', methods=['POST'])
@login_required
@student_required
def resume_polish():
    """
    AI bullet and description polisher.
    Takes rough student notes and converts them to ATS-friendly action statements.
    """
    data = request.get_json() or {}
    raw_text = data.get('text', '').strip()
    context_type = data.get('context_type', 'project')

    if not raw_text:
        return jsonify({'success': False, 'error': 'No text provided'}), 400

    polished = AIResumeService.polish_text_with_ai(raw_text, context_type=context_type)
    return jsonify({
        'success': True,
        'original': raw_text,
        'polished': polished
    })


@student_bp.route('/resume/save', methods=['POST'])
@login_required
@student_required
def save_resume():
    """
    Persist student's resume data to MySQL / SQLite.
    """
    student = current_user.student_profile
    if not student:
        return jsonify({'success': False, 'error': 'Student profile not found'}), 404

    payload = request.get_json() or {}
    resume_content = payload.get('resume_data', {})
    title = payload.get('title', 'Professional Tech Resume')

    try:
        resume_record = Resume.query.filter_by(student_id=student.id).first()
        if not resume_record:
            resume_record = Resume(
                student_id=student.id,
                title=title,
                data=resume_content
            )
            db.session.add(resume_record)
        else:
            resume_record.title = title
            resume_record.data = resume_content

        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Resume saved successfully!',
            'resume': resume_record.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@student_bp.route('/resume/preview')
@login_required
@student_required
def resume_preview():
    """
    Full ATS-formatted preview and print-ready export of the generated resume.
    """
    student = current_user.student_profile
    if not student:
        flash("Student profile not found.", "error")
        return redirect(url_for('student.dashboard'))

    certificates = Certificate.query.filter_by(student_id=student.id, status='issued').all()
    saved_resume = Resume.query.filter_by(student_id=student.id).first()
    
    resume_data = saved_resume.data if (saved_resume and saved_resume.data) else {}
    
    # Fallback to auto-generated default if not yet saved
    if not resume_data:
        cgpa_strategy = AIResumeService.analyze_cgpa_strategy(student.cgpa)
        resume_data = {
            'personal_info': {
                'name': current_user.name,
                'email': current_user.email,
                'phone': '+91 98765 43210',
                'location': student.user.college_name or 'India',
                'github': f"github.com/{current_user.name.lower().replace(' ', '')}",
                'linkedin': f"linkedin.com/in/{current_user.name.lower().replace(' ', '')}"
            },
            'summary': f"Proactive {student.degree} candidate with verified academic credentials and practical experience in software engineering.",
            'academic': {
                'degree': student.degree,
                'department': student.department,
                'college': current_user.college_name or 'BlockCert Institute',
                'graduation_year': student.graduation_year,
                'cgpa': student.cgpa
            },
            'cgpa_strategy': cgpa_strategy,
            'technical_skills': {
                'languages': ['Python', 'JavaScript', 'SQL'],
                'frameworks_and_tools': ['Flask', 'Git', 'REST APIs', 'MySQL']
            },
            'projects': [
                {
                    'title': 'Decentralized Credential Verification System',
                    'role': 'Full Stack Developer',
                    'technologies': ['Python', 'Flask', 'Web3', 'MySQL'],
                    'polished_bullets': [
                        'Engineered a secure credential verification platform utilizing SHA-256 cryptographic hashing.',
                        'Integrated smart contract verification logic to eliminate academic credential fraud.'
                    ]
                }
            ],
            'experience': [],
            'selected_certificates': [
                {
                    'certificate_id': c.certificate_id,
                    'course': c.course,
                    'issuer': c.issuer.college_name if c.issuer and c.issuer.college_name else 'BlockCert Institute',
                    'tx_hash': c.blockchain_tx_hash,
                    'year': c.graduation_year
                }
                for c in certificates
            ]
        }

    return render_template(
        'student/resume_preview.html',
        student=student,
        certificates=certificates,
        resume=resume_data
    )


@student_bp.route('/resume/data')
@login_required
@student_required
def get_resume_data():
    student = current_user.student_profile
    if not student:
        return jsonify({'success': False, 'error': 'Profile not found'}), 404

    saved_resume = Resume.query.filter_by(student_id=student.id).first()
    certificates = Certificate.query.filter_by(student_id=student.id, status='issued').all()

    return jsonify({
        'success': True,
        'resume': saved_resume.to_dict() if saved_resume else None,
        'certificates': [c.to_dict() for c in certificates],
        'cgpa_strategy': AIResumeService.analyze_cgpa_strategy(student.cgpa)
    })
