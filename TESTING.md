# BlockCert — Testing & Verification Guide

This guide details how to set up, run, and manually verify the **BlockCert** blockchain-backed certificate verification platform, including full tamper-detection validation.

---

## 1. Prerequisites & Quickstart

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Environment Configuration
Ensure `.env` exists (copied from `.env.example`):
```env
FLASK_ENV=development
SECRET_KEY=blockcert-dev-secret-key-2025
DATABASE_URL=sqlite:///blockcert.db
GANACHE_RPC_URL=http://127.0.0.1:8545
CONTRACT_ADDRESS=
ISSUER_ADDRESS=
UPLOAD_FOLDER=app/static/uploads/certificates
QR_FOLDER=app/static/uploads/qrcodes
```

---

## 2. Ganache & Smart Contract Deployment

1. **Start Ganache** (GUI on port 8545 or CLI `npx ganache -p 8545`).
2. **Deploy the Solidity Contract**:
   ```bash
   python scripts/deploy_contract.py
   ```
   *This will compile `contracts/Certificate.sol`, deploy to Ganache, and automatically update `.env` with the new `CONTRACT_ADDRESS` and `ISSUER_ADDRESS`.*

---

## 3. Seed Demo Accounts & Data

Populate the database with pre-configured role-based demo accounts:
```bash
python scripts/seed.py
```

### Demo Accounts
| Role | Email | Password | Details |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@blockcert.edu` | `Admin@123` | Issuing authority (Prof. Alistair Vance) |
| **Student** | `student@blockcert.edu` | `Student@123` | Alex Johnson (`STU-2025-0101`, B.S. CS) |
| **Student** | `jane@blockcert.edu` | `Student@123` | Jane Doe (`STU-2025-0102`, M.S. Cyber) |
| **Employer** | `employer@acme.com` | `Employer@123` | Sarah Connor (Talent Lead, Acme Corp) |

---

## 4. Run the Flask Web App

```bash
python run.py
```
Open **http://127.0.0.1:5000** in your web browser.

---

## 5. End-to-End User Journeys

### A. Admin Issuance Flow
1. Navigate to **http://127.0.0.1:5000/auth/login** and sign in as `admin@blockcert.edu` / `Admin@123`.
2. Click **Issue Certificate** in the top navigation or dashboard.
3. Select a student (e.g. Jane Doe), enter a Certificate ID (`CERT-2025-0002`), Course Name, and upload a document (PDF/PNG/JPG).
4. Notice the live client-side SHA-256 computation in the preview card.
5. Click **Mint On Blockchain**.
6. The contract method `issueCertificate` executes on Ganache, generating an immutable transaction hash, and stores the QR code.

### B. Student Dashboard & QR Code Download
1. Sign in as `student@blockcert.edu` / `Student@123`.
2. View your issued certificates.
3. Click the **QR Code** icon to open the interactive modal with the live verification URL.
4. Click the **Download** icon to download the authentic certificate file.

### C. Employer Search & Audit
1. Sign in as `employer@acme.com` / `Employer@123`.
2. Enter Certificate ID `CERT-2025-0001` in the verification box and submit.
3. Review the on-chain confirmation, block timestamp, and cryptographic match status.
4. View your **Audit History** to see all past verification attempts.

---

## 6. How to Verify Tamper Detection

BlockCert enforces zero-trust: **the blockchain is the sole source of truth**. If even a single byte of a stored certificate document is altered on disk, verification immediately fails.

### Option A: Automated Tamper Test Script
Run the automated test script:
```bash
python scripts/tamper_test.py CERT-2025-0001
```
Output walkthrough:
1. Reads `app/static/uploads/certificates/CERT-2025-0001.pdf` and confirms initial hash matches blockchain -> **`VERIFIED`**.
2. Appends simulated malicious bytes to the file on disk.
3. Recomputes SHA-256 hash and compares against on-chain anchor -> **`TAMPERED`** alert triggered.
4. Restores original file bytes -> Returns to **`VERIFIED`**.

### Option B: Manual UI Tampering Verification
1. Visit the public URL: **http://127.0.0.1:5000/verify/CERT-2025-0001**
   - Result: **VERIFIED** banner (Green), with blockchain transaction hash and block timestamp.
2. Open `app/static/uploads/certificates/CERT-2025-0001.pdf` in any text or hex editor.
3. Add a single letter (e.g., `X`) at the end of the file and save.
4. Refresh **http://127.0.0.1:5000/verify/CERT-2025-0001** in your browser.
   - Result: **SECURITY ALERT: TAMPERED CERTIFICATE** banner (Red), showing the recomputed hash versus the immutable blockchain hash.
5. Every tampering check is permanently recorded in `VerificationLog`.

---

## 7. Automated Test Suite

Run all unit and integration tests with `pytest`:
```bash
pytest -v
```
Tests cover:
- Cryptographic SHA-256 hashing and single-bit tamper detection (`tests/test_hashing.py`)
- User, Student, Certificate, and VerificationLog models (`tests/test_models.py`)
- Role-based authentication and redirection (`tests/test_auth.py`)
- Public verification, JSON API, and file tamper validation (`tests/test_verification.py`)
