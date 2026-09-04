import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.student import Student
from app.models.certificate import Certificate
from app.models.verification_log import VerificationLog


@pytest.fixture
def app_ctx():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_user_creation_and_roles(app_ctx):
    admin = User(name='Admin User', email='admin@test.com', role='admin')
    admin.set_password('AdminPass123')
    
    student_user = User(name='Student User', email='student@test.com', role='student')
    student_user.set_password('StudentPass123')

    employer = User(name='Employer User', email='employer@test.com', role='employer')
    employer.set_password('EmployerPass123')

    db.session.add_all([admin, student_user, employer])
    db.session.commit()

    assert admin.is_admin is True
    assert admin.is_student is False
    assert admin.check_password('AdminPass123') is True
    assert admin.check_password('WrongPass') is False

    assert student_user.is_student is True
    assert employer.is_employer is True


def test_student_and_certificate_relationships(app_ctx):
    admin = User(name='Admin', email='admin@test.com', role='admin')
    admin.set_password('pass123')

    student_user = User(name='Student Jane', email='jane@test.com', role='student')
    student_user.set_password('pass123')
    db.session.add_all([admin, student_user])
    db.session.flush()

    student = Student(
        user_id=student_user.id,
        roll_number='STU-999',
        degree='B.S. CS',
        department='CS',
        graduation_year=2025
    )
    db.session.add(student)
    db.session.flush()

    cert = Certificate(
        certificate_id='CERT-TEST-001',
        student_id=student.id,
        issuer_id=admin.id,
        course='Blockchain Fundamentals',
        graduation_year=2025,
        file_path='uploads/certificates/test.pdf',
        sha256_hash='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        blockchain_tx_hash='0x1234567890abcdef',
        qr_code_path='uploads/qrcodes/test_qr.png',
        status='issued'
    )
    db.session.add(cert)
    db.session.commit()

    assert student.user.email == 'jane@test.com'
    assert cert.student.roll_number == 'STU-999'
    assert cert.issuer.name == 'Admin'

    # Verification Log
    log = VerificationLog(
        certificate_id='CERT-TEST-001',
        certificate_db_id=cert.id,
        result='verified',
        attempted_hash=cert.sha256_hash
    )
    db.session.add(log)
    db.session.commit()

    assert log.certificate.course == 'Blockchain Fundamentals'
    assert log.result == 'verified'
