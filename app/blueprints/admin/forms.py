from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, IntegerField, SelectField, SubmitField, FloatField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Email, ValidationError
from app.models.certificate import Certificate
from app.models.user import User


class IssueCertificateForm(FlaskForm):
    student_id = SelectField('Select Student', coerce=int, validators=[DataRequired(message='Please select a student.')])
    certificate_id = StringField('Certificate ID', validators=[
        DataRequired(message='Certificate ID is required.'),
        Length(min=3, max=100)
    ], description="e.g. CERT-2025-0001")
    course = StringField('Course / Degree Name', validators=[
        DataRequired(message='Course / Degree name is required.'),
        Length(min=2, max=150)
    ], description="e.g. Bachelor of Science in Computer Science")
    graduation_year = IntegerField('Graduation Year', validators=[
        DataRequired(message='Graduation year is required.'),
        NumberRange(min=1950, max=2100)
    ])
    certificate_file = FileField('Certificate Document (PDF/PNG/JPG)', validators=[
        FileRequired(message='Please upload a certificate document file.'),
        FileAllowed(['pdf', 'png', 'jpg', 'jpeg'], 'Only PDF, PNG, and JPG files are supported.')
    ])
    submit = SubmitField('Issue Secure Certificate')

    def validate_certificate_id(self, field):
        existing = Certificate.query.filter_by(certificate_id=field.data.strip()).first()
        if existing:
            raise ValidationError(f"Certificate ID '{field.data}' is already in use. Please use a unique ID.")


class StudentForm(FlaskForm):
    name = StringField('Full Legal Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    roll_number = StringField('Roll / Student ID', validators=[DataRequired(), Length(min=2, max=50)])
    degree = StringField('Degree / Program', validators=[DataRequired(), Length(min=2, max=100)])
    department = StringField('Department', validators=[DataRequired(), Length(min=2, max=100)])
    graduation_year = IntegerField('Graduation Year', validators=[DataRequired(), NumberRange(min=1950, max=2100)])
    cgpa = FloatField('CGPA / Percentage', validators=[Optional(), NumberRange(min=0.0, max=10.0)])
    password = StringField('Default Password', default='Student@123', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register Student')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError('A user with this email address already exists.')
