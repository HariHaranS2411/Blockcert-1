from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, IntegerField, FloatField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange, ValidationError
from app.models.user import User


class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class SignupForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    role = SelectField('Account Role', choices=[
        ('student', 'Student / Graduate'),
        ('admin', 'College Administrator / Issuer'),
        ('employer', 'Employer / Verifier')
    ], default='student', validators=[DataRequired()])
    college_name = StringField('College / Institution Name', validators=[Optional(), Length(max=150)])
    
    # Student specific fields
    roll_number = StringField('Roll / Registration Number', validators=[Optional(), Length(max=50)])
    degree = StringField('Degree (e.g. B.Tech, B.S.)', validators=[Optional(), Length(max=100)])
    department = StringField('Department / Major', validators=[Optional(), Length(max=100)])
    graduation_year = IntegerField('Graduation Year', validators=[Optional(), NumberRange(min=1950, max=2100)])
    cgpa = FloatField('CGPA / Percentage', validators=[Optional(), NumberRange(min=0.0, max=10.0)])

    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Create Account')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError('An account with this email address already exists.')

    def validate_roll_number(self, field):
        if self.role.data == 'student' and not field.data:
            raise ValidationError('Roll number is required for student accounts.')
