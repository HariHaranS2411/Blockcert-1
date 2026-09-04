from datetime import datetime, timezone
from app.extensions import db


class VerificationLog(db.Model):
    __tablename__ = 'verification_logs'

    id = db.Column(db.Integer, primary_key=True)
    certificate_id = db.Column(db.String(100), nullable=False, index=True)
    certificate_db_id = db.Column(db.Integer, db.ForeignKey('certificates.id', ondelete='SET NULL'), nullable=True)
    verifier_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    result = db.Column(db.String(20), nullable=False)  # verified, tampered, not_found
    attempted_hash = db.Column(db.String(64), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    certificate = db.relationship('Certificate', back_populates='verification_logs', foreign_keys=[certificate_db_id])
    verifier = db.relationship('User', back_populates='verification_logs', foreign_keys=[verifier_id])

    def to_dict(self):
        return {
            'id': self.id,
            'certificate_id': self.certificate_id,
            'certificate_db_id': self.certificate_db_id,
            'verifier_id': self.verifier_id,
            'verifier_name': self.verifier.name if self.verifier else 'Public/Anonymous',
            'result': self.result,
            'attempted_hash': self.attempted_hash,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<VerificationLog {self.certificate_id} - {self.result}>'
