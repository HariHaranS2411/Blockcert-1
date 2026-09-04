from app.extensions import db


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    roll_number = db.Column(db.String(50), nullable=False, index=True)
    degree = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    graduation_year = db.Column(db.Integer, nullable=False)
    cgpa = db.Column(db.Float, nullable=True)

    # Relationships
    user = db.relationship('User', back_populates='student_profile')
    certificates = db.relationship('Certificate', back_populates='student', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.user.name if self.user else None,
            'email': self.user.email if self.user else None,
            'college_name': self.user.college_name if self.user else None,
            'roll_number': self.roll_number,
            'degree': self.degree,
            'department': self.department,
            'graduation_year': self.graduation_year,
            'cgpa': self.cgpa
        }

    def __repr__(self):
        return f'<Student {self.roll_number} (User {self.user_id})>'
