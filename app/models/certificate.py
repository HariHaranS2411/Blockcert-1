from datetime import datetime, timezone
from app.extensions import db


class Certificate(db.Model):
    __tablename__ = 'certificates'

    id = db.Column(db.Integer, primary_key=True)
    certificate_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    issuer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course = db.Column(db.String(150), nullable=False)
    graduation_year = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(300), nullable=False)
    sha256_hash = db.Column(db.String(64), nullable=False, index=True)
    blockchain_tx_hash = db.Column(db.String(100), nullable=False)
    qr_code_path = db.Column(db.String(300), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='issued')  # issued, revoked
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student = db.relationship('Student', back_populates='certificates')
    issuer = db.relationship('User', back_populates='issued_certificates', foreign_keys=[issuer_id])
    verification_logs = db.relationship('VerificationLog', back_populates='certificate', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'certificate_id': self.certificate_id,
            'student_id': self.student_id,
            'student_name': self.student.user.name if self.student and self.student.user else None,
            'student_email': self.student.user.email if self.student and self.student.user else None,
            'roll_number': self.student.roll_number if self.student else None,
            'issuer_id': self.issuer_id,
            'issuer_name': self.issuer.name if self.issuer else None,
            'college_name': self.issuer.college_name if self.issuer else (self.student.user.college_name if self.student and self.student.user else None),
            'course': self.course,
            'graduation_year': self.graduation_year,
            'file_path': self.file_path,
            'sha256_hash': self.sha256_hash,
            'blockchain_tx_hash': self.blockchain_tx_hash,
            'qr_code_path': self.qr_code_path,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Certificate {self.certificate_id} ({self.status})>'
