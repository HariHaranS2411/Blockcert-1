import os
import pytest
from pathlib import Path
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.student import Student
from app.models.certificate import Certificate
from app.blockchain.hashing import compute_bytes_sha256


@pytest.fixture
def client(tmp_path):
    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'certificates')
    app.config['QR_FOLDER'] = str(tmp_path / 'qrcodes')
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.config['QR_FOLDER']).mkdir(parents=True, exist_ok=True)

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()


def test_public_verify_not_found(client):
    res = client.get('/verify/NON-EXISTENT-ID')
    assert res.status_code == 200
    assert b"Certificate Not Found" in res.data


def test_api_verify_endpoint(client, tmp_path):
    # Setup test student, cert file, and certificate row
    admin = User(name='Admin', email='admin@test.com', role='admin')
    admin.set_password('pass')
    student_user = User(name='Bob', email='bob@test.com', role='student')
    student_user.set_password('pass')
    db.session.add_all([admin, student_user])
    db.session.flush()

    student = Student(user_id=student_user.id, roll_number='STU-BOB', degree='B.S.', department='CS', graduation_year=2025)
    db.session.add(student)
    db.session.flush()

    # Create dummy file on disk
    file_content = b"%PDF-1.4 Certificate Test Document"
    file_hash = compute_bytes_sha256(file_content)
    
    cert_dir = Path(client.application.config['UPLOAD_FOLDER'])
    file_on_disk = cert_dir / "CERT-TEST-001.pdf"
    with open(file_on_disk, 'wb') as f:
        f.write(file_content)

    cert = Certificate(
        certificate_id='CERT-TEST-001',
        student_id=student.id,
        issuer_id=admin.id,
        course='Cybersecurity 101',
        graduation_year=2025,
        file_path='uploads/certificates/CERT-TEST-001.pdf',
        sha256_hash=file_hash,
        blockchain_tx_hash='0x123456',
        qr_code_path='uploads/qrcodes/CERT-TEST-001_qr.png',
        status='issued'
    )
    db.session.add(cert)
    db.session.commit()

    # 1. Verify endpoint returns JSON
    res = client.get('/api/verify/CERT-TEST-001')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['success'] is True
    assert json_data['is_verified'] is True
    assert json_data['result'] == 'verified'
    assert json_data['recomputed_hash'] == file_hash

    # 2. Simulate File Tampering on disk
    with open(file_on_disk, 'wb') as f:
        f.write(file_content + b"[FORGED_DATA]")

    res = client.get('/api/verify/CERT-TEST-001')
    assert res.status_code == 200
    tampered_json = res.get_json()
    assert tampered_json['is_verified'] is False
    assert tampered_json['result'] == 'tampered'
    assert tampered_json['recomputed_hash'] != file_hash
