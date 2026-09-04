import json
from datetime import datetime, timezone
from app.extensions import db


class Resume(db.Model):
    __tablename__ = 'resumes'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), unique=True, nullable=False)
    title = db.Column(db.String(150), default='Professional Tech Resume')
    raw_data = db.Column(db.Text, nullable=False, default='{}')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    student = db.relationship('Student', backref=db.backref('resume', uselist=False, cascade='all, delete-orphan'))

    @property
    def data(self):
        try:
            return json.loads(self.raw_data)
        except Exception:
            return {}

    @data.setter
    def data(self, value):
        if isinstance(value, dict):
            self.raw_data = json.dumps(value)
        elif isinstance(value, str):
            self.raw_data = value
        else:
            self.raw_data = json.dumps({})

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'title': self.title,
            'data': self.data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Resume student_id={self.student_id} title="{self.title}">'
