import os
from pathlib import Path
from datetime import datetime
from flask import render_template, request, jsonify, current_app, send_file, abort
from flask_login import current_user
from app.extensions import db
from app.models.certificate import Certificate
from app.models.verification_log import VerificationLog
from app.blueprints.verify import verify_bp
from app.blockchain.hashing import compute_file_sha256
from app.blockchain.contract import blockchain_client


@verify_bp.route('/')
def landing():
    return render_template('verify/landing.html')


@verify_bp.route('/verify/<certificate_id>')
def verify_certificate_view(certificate_id):
    cert_id = certificate_id.strip()
    verifier_id = current_user.id if current_user.is_authenticated else None
    ip_address = request.remote_addr

    # 1. Look up certificate in database
    cert = Certificate.query.filter_by(certificate_id=cert_id).first()

    computed_file_hash = None
    onchain_data = {'hash': None, 'issuer': None, 'timestamp': None, 'exists': False}
    result = 'not_found'
    tx_hash = None
    file_exists = False

    # 2. Check on-chain record if blockchain is connected
    try:
        if blockchain_client.is_connected() and blockchain_client.get_contract_address():
            onchain_data = blockchain_client.get_certificate_hash_onchain(cert_id)
    except Exception as e:
        current_app.logger.warning(f"On-chain query failed during verification: {e}")

    # 3. If certificate exists in DB, compute SHA-256 from actual file
    if cert:
        tx_hash = cert.blockchain_tx_hash
        base_dir = Path(current_app.root_path)
        file_path = base_dir / 'static' / cert.file_path

        if not file_path.exists():
            # Check configured upload folder
            file_path = Path(current_app.config['UPLOAD_FOLDER']) / Path(cert.file_path).name

        if file_path.exists():
            file_exists = True
            computed_file_hash = compute_file_sha256(str(file_path))

            # Compare recomputed file hash against on-chain hash
            if onchain_data.get('exists') and onchain_data.get('hash'):
                if computed_file_hash.lower() == onchain_data['hash'].lower():
                    result = 'verified'
                else:
                    # File on disk differs from blockchain immutable record -> TAMPERED!
                    result = 'tampered'
            else:
                # If blockchain not queried or not found on-chain, compare against DB hash for fallback
                if computed_file_hash.lower() == cert.sha256_hash.lower():
                    result = 'verified'
                else:
                    result = 'tampered'
        else:
            # File missing from disk
            result = 'tampered'
    else:
        # Certificate not in DB
        if onchain_data.get('exists'):
            result = 'verified'
        else:
            result = 'not_found'

    # 4. Log the verification attempt in VerificationLog
    try:
        log_entry = VerificationLog(
            certificate_id=cert_id,
            certificate_db_id=cert.id if cert else None,
            verifier_id=verifier_id,
            result=result,
            attempted_hash=computed_file_hash or onchain_data.get('hash'),
            ip_address=ip_address
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to save VerificationLog: {e}")

    # Format timestamp for display
    block_timestamp_str = None
    if onchain_data.get('timestamp') and onchain_data['timestamp'] > 0:
        block_timestamp_str = datetime.utcfromtimestamp(onchain_data['timestamp']).strftime('%b-%d-%Y %H:%M:%S UTC')
    elif cert and cert.created_at:
        block_timestamp_str = cert.created_at.strftime('%b-%d-%Y %H:%M:%S UTC')

    # 5. Return JSON if requested or on /api/ route
    if request.path.startswith('/api/') or request.is_json or request.args.get('format') == 'json':
        return jsonify({
            'success': True,
            'certificate_id': cert_id,
            'result': result,
            'is_verified': (result == 'verified'),
            'recomputed_hash': computed_file_hash,
            'blockchain_hash': onchain_data.get('hash') or (cert.sha256_hash if cert else None),
            'blockchain_tx_hash': tx_hash,
            'issuer_address': onchain_data.get('issuer'),
            'timestamp': block_timestamp_str,
            'certificate': cert.to_dict() if cert else None
        })

    # 6. Render verification result template
    return render_template(
        'verify/result.html',
        certificate_id=cert_id,
        certificate=cert,
        result=result,
        computed_hash=computed_file_hash,
        onchain_hash=onchain_data.get('hash'),
        issuer_address=onchain_data.get('issuer'),
        block_timestamp=block_timestamp_str,
        tx_hash=tx_hash
    )


@verify_bp.route('/api/verify/<certificate_id>')
def api_verify(certificate_id):
    """Clean JSON API endpoint for certificate verification."""
    return verify_certificate_view(certificate_id)


@verify_bp.route('/verify/download/<certificate_id>')
def public_download(certificate_id):
    """Public download if verified certificate."""
    cert = Certificate.query.filter_by(certificate_id=certificate_id.strip()).first_or_404()
    
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
