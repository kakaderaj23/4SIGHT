from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, FloatField
from wtforms.validators import DataRequired
from wtforms import TextAreaField
from wtforms import PasswordField


JOB_TYPES = [
    ('turning', 'Turning'),
    ('facing', 'Facing'),
    ('threading', 'Threading'),
    ('drilling', 'Drilling'),
    ('boring', 'Boring'),
    ('knurling', 'Knurling')
]

MATERIALS = [
    ('Mild Steel', 'Mild Steel'),
    ('Aluminum', 'Aluminum'),
    ('Wood', 'Wood'),
    ('Custom', 'Custom')
]

class JobForm(FlaskForm):
    job_type = SelectField('Job Type', choices=JOB_TYPES, validators=[DataRequired()])
    job_description = StringField('Job Description', validators=[DataRequired()])
    material = SelectField('Material', choices=MATERIALS, validators=[DataRequired()])
    tool_no = IntegerField('Tool Number', validators=[DataRequired()])
    estimated_time = FloatField('Estimated Execution Time (minutes)', validators=[DataRequired()])
    operator_name = StringField('Operator Name', validators=[DataRequired()])



class AlertForm(FlaskForm):
    message = TextAreaField('Alert Message', validators=[DataRequired()])


class LoginForm(FlaskForm):
    userID = StringField("User ID", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
