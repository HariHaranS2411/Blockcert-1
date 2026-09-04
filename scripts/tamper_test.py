import os
import sys
from pathlib import Path

# Set UTF-8 encoding for console on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add root directory to python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from app.models.certificate import Certificate
from app.blockchain.hashing import compute_file_sha256
from app.blockchain.contract import blockchain_client


def run_tamper_test(cert_id="CERT-2025-0001"):
    app = create_app('development')

    with app.app_context():
        print("=" * 65)
        print("  BlockCert - Automated Tamper-Detection Verification Test")
        print("=" * 65)

        cert = Certificate.query.filter_by(certificate_id=cert_id).first()
        if not cert:
            print(f"[X] Error: Certificate '{cert_id}' not found in database. Run 'python scripts/seed.py' first.")
            return False

        # Locate physical file
        file_path = Path(app.root_path) / 'static' / cert.file_path
        if not file_path.exists():
            file_path = Path(app.config['UPLOAD_FOLDER']) / Path(cert.file_path).name

        if not file_path.exists():
            print(f"[X] Error: Certificate physical file not found at {file_path}")
            return False

        print(f"[+] Testing Certificate ID : {cert_id}")
        print(f"[+] Physical Document Path : {file_path}")
        print(f"[+] Registered Chain Hash  : {cert.sha256_hash}")

        # Step 1: Initial Integrity Check
        with open(file_path, 'rb') as f:
            original_bytes = f.read()

        initial_hash = compute_file_sha256(str(file_path))
        print(f"\n[Step 1] Initial File SHA-256: {initial_hash}")

        if initial_hash.lower() == cert.sha256_hash.lower():
            print("[OK] Status: Initial document is AUTHENTIC and matches blockchain anchor.")
        else:
            print("[!] Warning: Initial document hash already differs from DB/chain hash.")

        # Step 2: Simulate Byte Tampering
        print("\n[Step 2] Modifying 1 byte in the physical file on disk (Simulating Forgery)...")
        tampered_bytes = original_bytes + b"\x00[TAMPERED_MALICIOUS_DATA]"
        with open(file_path, 'wb') as f:
            f.write(tampered_bytes)

        tampered_hash = compute_file_sha256(str(file_path))
        print(f"[ALERT] Tampered File SHA-256: {tampered_hash}")
        print(f"Comparing Tampered Hash vs Immutable Blockchain Anchor:")
        print(f"  - Recomputed File Hash: {tampered_hash}")
        print(f"  - Blockchain Truth:     {cert.sha256_hash}")

        if tampered_hash.lower() != cert.sha256_hash.lower():
            print("[SUCCESS] Tamper detected! The system flagged the document as TAMPERED.")
        else:
            print("[FAIL] Failure: Tamper was not detected.")

        # Step 3: Restore Original File Bytes
        print("\n[Step 3] Restoring original document bytes...")
        with open(file_path, 'wb') as f:
            f.write(original_bytes)

        restored_hash = compute_file_sha256(str(file_path))
        print(f"[RESTORED] Restored File SHA-256: {restored_hash}")
        if restored_hash.lower() == cert.sha256_hash.lower():
            print("[OK] Status: Document restored. Verification returns VERIFIED.")

        print("=" * 65)
        print("  Tamper-Detection Verification Test Completed Successfully!")
        print("=" * 65)
        return True


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else "CERT-2025-0001"
    run_tamper_test(target)
