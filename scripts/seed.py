import os
import sys
from pathlib import Path
from flask import url_for

# Set UTF-8 encoding for console on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add root directory to python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.student import Student
from app.models.certificate import Certificate
from app.models.verification_log import VerificationLog
from app.blockchain.hashing import compute_file_sha256
from app.blockchain.qr import generate_certificate_qr
from app.blockchain.contract import blockchain_client


def seed():
    app = create_app('development')

    with app.app_context():
        print("=" * 60)
        print("  BlockCert - Database & Demo Account Seeder")
        print("=" * 60)

        # Create tables
        db.create_all()

        # 1. Seed Admin User
        admin = User.query.filter_by(email='admin@blockcert.edu').first()
        if not admin:
            admin = User(
                name='Prof. Alistair Vance',
                email='admin@blockcert.edu',
                role='admin',
                college_name='BlockCert Institute of Technology'
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
            print(" Created Admin: admin@blockcert.edu / Admin@123")
        else:
            print(" Admin user already exists.")

        # 2. Seed Student 1
        student1_user = User.query.filter_by(email='student@blockcert.edu').first()
        if not student1_user:
            student1_user = User(
                name='Alex Johnson',
                email='student@blockcert.edu',
                role='student',
                college_name='BlockCert Institute of Technology'
            )
            student1_user.set_password('Student@123')
            db.session.add(student1_user)
            db.session.flush()

            student1_profile = Student(
                user_id=student1_user.id,
                roll_number='STU-2025-0101',
                degree='B.S. Computer Science',
                department='Computer Science & Engineering',
                graduation_year=2025,
                cgpa=9.2
            )
            db.session.add(student1_profile)
            print(" Created Student 1: student@blockcert.edu / Student@123 (Alex Johnson)")
        else:
            student1_profile = student1_user.student_profile
            print(" Student 1 already exists.")

        # 3. Seed Student 2
        student2_user = User.query.filter_by(email='jane@blockcert.edu').first()
        if not student2_user:
            student2_user = User(
                name='Jane Doe',
                email='jane@blockcert.edu',
                role='student',
                college_name='BlockCert Institute of Technology'
            )
            student2_user.set_password('Student@123')
            db.session.add(student2_user)
            db.session.flush()

            student2_profile = Student(
                user_id=student2_user.id,
                roll_number='STU-2025-0102',
                degree='M.S. Cybersecurity',
                department='Information Security',
                graduation_year=2025,
                cgpa=9.6
            )
            db.session.add(student2_profile)
            print(" Created Student 2: jane@blockcert.edu / Student@123 (Jane Doe)")
        else:
            student2_profile = student2_user.student_profile
            print(" Student 2 already exists.")

        # 4. Seed Employer User
        employer = User.query.filter_by(email='employer@acme.com').first()
        if not employer:
            employer = User(
                name='Sarah Connor (Talent Lead)',
                email='employer@acme.com',
                role='employer',
                college_name='Acme Global Technologies'
            )
            employer.set_password('Employer@123')
            db.session.add(employer)
            print(" Created Employer: employer@acme.com / Employer@123")
        else:
            print(" Employer user already exists.")

        db.session.commit()

        # 5. Seed Sample Demo Certificate
        cert_id = "CERT-2025-0001"
        existing_cert = Certificate.query.filter_by(certificate_id=cert_id).first()
        if not existing_cert and student1_profile:
            # Create sample document file
            upload_dir = Path(app.config['UPLOAD_FOLDER'])
            upload_dir.mkdir(parents=True, exist_ok=True)
            doc_file = upload_dir / f"{cert_id}.pdf"

            # Write demo PDF content
            with open(doc_file, 'wb') as f:
                f.write(b"%PDF-1.4\n%BlockCert Demo Academic Credential - Alex Johnson - B.S. Computer Science - 2025\n%%EOF\n")

            sha256_hash = compute_file_sha256(str(doc_file))

            # Try to register on blockchain if Ganache is active
            tx_hash = "0x" + "0" * 64
            if blockchain_client.is_connected() and blockchain_client.get_contract_address():
                try:
                    if not blockchain_client.certificate_exists_onchain(cert_id):
                        tx_res = blockchain_client.issue_certificate_onchain(cert_id, sha256_hash)
                        tx_hash = tx_res['tx_hash']
                        print(f" Anchored {cert_id} to Ganache! Tx: {tx_hash}")
                    else:
                        print(f" Certificate {cert_id} is already anchored on-chain.")
                except Exception as e:
                    print(f"[!] Warning: Could not anchor demo cert to blockchain: {e}")

            # Generate QR Code
            qr_dir = Path(app.config['QR_FOLDER'])
            qr_dir.mkdir(parents=True, exist_ok=True)
            verify_url = f"http://127.0.0.1:5000/verify/{cert_id}"
            qr_file = generate_certificate_qr(cert_id, verify_url, str(qr_dir))

            sample_cert = Certificate(
                certificate_id=cert_id,
                student_id=student1_profile.id,
                issuer_id=admin.id,
                course='Bachelor of Science in Computer Science',
                graduation_year=2025,
                file_path=f"uploads/certificates/{cert_id}.pdf",
                sha256_hash=sha256_hash,
                blockchain_tx_hash=tx_hash,
                qr_code_path=f"uploads/qrcodes/{Path(qr_file).name}",
                status='issued'
            )
            db.session.add(sample_cert)

            # Verification Log demo
            log = VerificationLog(
                certificate_id=cert_id,
                verifier_id=employer.id,
                result='verified',
                attempted_hash=sha256_hash,
                ip_address='127.0.0.1'
            )
            db.session.add(log)
            db.session.commit()
            print(f" Created sample certificate: {cert_id}")

        print("\n" + "=" * 60)
        print("  Demo Accounts Ready:")
        print("  --------------------------------------------------")
        print("  [Admin]    admin@blockcert.edu    / Admin@123")
        print("  [Student]  student@blockcert.edu  / Student@123")
        print("  [Student]  jane@blockcert.edu     / Student@123")
        print("  [Employer] employer@acme.com      / Employer@123")
        print("=" * 60)


if __name__ == '__main__':
    seed()
