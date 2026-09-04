from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class CertificateSearchForm(FlaskForm):
    certificate_id = StringField('Certificate ID', validators=[
        DataRequired(message='Please enter a Certificate ID.'),
        Length(min=3, max=100)
    ], render_kw={"placeholder": "e.g. CERT-2025-0001, BC-2023-1024"})
    submit = SubmitField('Verify Authenticity')
